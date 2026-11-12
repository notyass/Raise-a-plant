"""Méthode n°2, vectorielle : des distances dans un espace vectoriel.

Idée : représenter chaque fiche par une liste de nombres (un vecteur), la
demande aussi, puis mesurer leur proximité. Plus les deux vecteurs sont
proches, meilleur est le score.

  - O2 (plantes pour un environnement) : une fiche devient un point dont les
    coordonnées sont sa lumière, son eau, sa difficulté... entre 0 et 1. Les
    curseurs de l'utilisateur donnent un autre point. Le score est
    1 - distance entre les deux points.
  - O1 (retrouver une plante) : un texte devient le vecteur de ses paires de
    lettres (« tomate » -> to, om, ma, at, te). Deux textes qui partagent
    beaucoup de paires sont proches, même avec une faute de frappe. On
    compare la recherche au nom, au nom latin et au type de chaque fiche, et
    on garde la meilleure des ressemblances.

Cette méthode renvoie toujours les fiches les plus proches, même si aucune
ne convient parfaitement : elle est souple, mais ne garantit rien.
"""
import time

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

from app.services.query_builder import CRITERIA, WEIGHTS, codes_position
from app.services.recommenders.base import BaseRecommender, Recommendation, ease_rank

# O1 : en dessous de ce score, la fiche ne ressemble pas assez à la recherche.
MIN_SEARCH_SCORE = 0.4
MAX_EXPLANATION_TERMS = 5
# O1 : parties d'une fiche comparées à la recherche.
SEARCH_FIELDS = ("name", "scientific_name", "category_fr", "category_en")

# O2 : critères numériques (une coordonnée entre 0 et 1 chacun)...
NUMERIC_KEYS = ("sun", "water", "difficulty")
# ... et critères « oui / non » (une coordonnée 0 ou 1 par valeur possible).
BINARY_KEYS = ("season", "soil")


class VectorRecommender(BaseRecommender):
    key = "vector"
    label = "Vectorielle (distance dans un espace vectoriel)"
    description = (
        "Chaque fiche est un point dans un espace de nombres. On mesure la "
        "distance entre la demande et chaque fiche, et on garde les plus "
        "proches. Il y a toujours un résultat, même approximatif."
    )
    explanations = {
        "care": (
            "Paires de lettres communes à ta recherche et à la partie de la fiche "
            "qui lui ressemble le plus (nom, nom latin ou type), avec leur part "
            "dans le score (« _ » marque un début ou une fin de mot)."
        ),
        "environment": (
            "Proximité entre ta demande et la fiche pour chaque critère "
            "(1 = identique, 0 = à l'opposé)."
        ),
    }
    complexity = {
        "notation": (
            "N = nombre de fiches, d = nombre de coordonnées d'une fiche (13), "
            "P = nombre moyen de paires de lettres par fiche (nom, nom latin, type)"
        ),
        "indexation": "O(N × d) pour les coordonnées + O(N × P) pour les paires de lettres, au premier appel",
        "recherche": "O(N × P) pour le produit matrice-vecteur + O(N log N) pour le tri",
        "recommandation": "O(N × d) pour les distances (calcul numpy) + O(N log N) pour le tri",
        "memoire": "O(N × d) + O(N × P)",
        "pistes": (
            "Ne garder que les k plus proches sans trier les N scores ; index "
            "spatial (arbre k-d) pour ne pas mesurer toutes les distances ; "
            "index inversé des paires de lettres pour la recherche."
        ),
    }

    def __init__(self):
        self.plant_ids = np.array([], dtype=int)
        self.ease = np.array([], dtype=int)
        # O1 : pour chaque partie de fiche (nom, nom latin, type), une matrice
        # creuse N × (nombre de paires de lettres), lignes de norme 1
        self.pair_vectorizer = CountVectorizer(analyzer="char_wb", ngram_range=(2, 2))
        self.pair_matrices = {}
        self.pairs = np.array([])
        # O2 : matrice dense N × d des coordonnées, et colonne de chaque coordonnée
        self.features = None
        self.columns = {}
        self.fit_duration_ms = None

    def fit(self, documents):
        start = time.perf_counter()
        self.plant_ids = np.array([doc.plant_id for doc in documents], dtype=int)
        self.ease = np.array([ease_rank(doc.attributes) for doc in documents], dtype=int)

        # --- O1 : vecteurs des paires de lettres de chaque partie de fiche ---
        texts = {field: [] for field in SEARCH_FIELDS}
        for doc in documents:
            categories = list(doc.names["categories"]) + ["", ""]  # complète si un nom manque
            texts["name"].append(doc.names["name"])
            texts["scientific_name"].append(doc.names["scientific_name"])
            texts["category_fr"].append(categories[0])
            texts["category_en"].append(categories[1])
        # le vocabulaire (toutes les paires de lettres existantes) est commun aux parties
        self.pair_vectorizer.fit([text for field in SEARCH_FIELDS for text in texts[field]])
        self.pairs = self.pair_vectorizer.get_feature_names_out()
        self.pair_matrices = {
            # normalize : chaque ligne est ramenée à une longueur de 1
            field: normalize(self.pair_vectorizer.transform(texts[field]))
            for field in SEARCH_FIELDS
        }

        # --- O2 : coordonnées de chaque fiche ---
        names = list(NUMERIC_KEYS)
        for key in BINARY_KEYS:
            names += [f"{key}:{choice['value']}" for choice in CRITERIA[key]["choices"]]
        names.append("container")
        self.columns = {name: column for column, name in enumerate(names)}

        self.features = np.zeros((len(documents), len(names)))
        for row, doc in enumerate(documents):
            attributes = doc.attributes
            for key in NUMERIC_KEYS:
                # moyenne des niveaux de la fiche ; NaN si la fiche ne dit rien
                position = codes_position(key, attributes.get(key, []))
                self.features[row, self.columns[key]] = np.nan if position is None else position
            for key in BINARY_KEYS:
                for code in attributes.get(key, []):
                    self.features[row, self.columns[f"{key}:{code}"]] = 1.0
            self.features[row, self.columns["container"]] = 1.0 if attributes.get("container") else 0.0

        self.fit_duration_ms = (time.perf_counter() - start) * 1000

    # ----- O1 : retrouver une plante par son nom -----

    def search(self, query, top_k=10):
        query_vector = normalize(self.pair_vectorizer.transform([query]))
        if query_vector.nnz == 0:
            return []  # aucune paire de lettres de la recherche n'existe dans les fiches

        # Vecteurs de longueur 1 : le produit scalaire est le cosinus de leur angle
        # (1 = mêmes paires de lettres, 0 = aucune en commun). Une colonne par partie.
        similarities = np.column_stack([
            (self.pair_matrices[field] @ query_vector.T).toarray().ravel()
            for field in SEARCH_FIELDS
        ])
        best_field = similarities.argmax(axis=1)  # partie la plus ressemblante de chaque fiche
        scores = similarities.max(axis=1)

        results = []
        for row in self._order(scores)[:top_k]:
            if scores[row] < MIN_SEARCH_SCORE:
                break  # les suivantes ne ressemblent pas assez à la recherche
            field = SEARCH_FIELDS[best_field[row]]
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(min(1.0, scores[row])),
                    matched_terms=self._explain_search(query_vector, field, row),
                )
            )
        return results

    def _explain_search(self, query_vector, field, row):
        """Paires de lettres communes, avec leur contribution au score."""
        contributions = query_vector.multiply(self.pair_matrices[field][row]).tocoo()
        ranked = sorted(zip(contributions.col, contributions.data), key=lambda pair: -pair[1])
        return [
            {"term": str(self.pairs[column]).replace(" ", "_"), "weight": round(float(weight), 4)}
            for column, weight in ranked[:MAX_EXPLANATION_TERMS]
        ]

    # ----- O2 : plantes pour un environnement -----

    def _target(self, part):
        """Colonne et valeur visée pour un critère de la demande."""
        key = part["key"]
        if key in NUMERIC_KEYS:
            return self.columns[key], part["value"]
        if key in BINARY_KEYS:
            return self.columns[f"{key}:{part['code']}"], 1.0
        if key == "container":
            return self.columns["container"], 1.0
        return None, None  # « category » : traité par le filtre allowed_ids

    def _gaps(self, parts):
        """Écart (entre 0 et 1) de chaque fiche à la demande, critère par critère.

        Renvoie un tableau N × (nombre de critères).
        """
        gaps = np.zeros((len(self.plant_ids), len(parts)))
        for index, part in enumerate(parts):
            column, target = self._target(part)
            if column is None:
                continue  # écart nul : les fiches hors catégorie sont déjà filtrées
            gap = np.abs(self.features[:, column] - target)
            gaps[:, index] = np.where(np.isnan(gap), 1.0, gap)  # fiche muette : écart maximal
        return gaps

    def recommend(self, query_parts, top_k=10, allowed_ids=None):
        parts = [part for part in query_parts if part["key"] in WEIGHTS]
        if not parts:
            return []
        weights = np.array([WEIGHTS[part["key"]] for part in parts], dtype=float)

        # 1. Distance euclidienne pondérée entre la demande et chaque fiche,
        #    ramenée entre 0 et 1, puis score = 1 - distance.
        gaps = self._gaps(parts)
        distances = np.sqrt((gaps ** 2 * weights).sum(axis=1) / weights.sum())
        scores = 1.0 - distances

        # 2. Filtre optionnel sur les identifiants (une seule catégorie).
        if allowed_ids is not None:
            allowed = np.isin(self.plant_ids, list(allowed_ids))
            scores = np.where(allowed, scores, -1.0)

        # 3. Les plus proches d'abord. Aucune fiche n'est éliminée par un critère.
        results = []
        for row in self._order(scores)[:top_k]:
            if scores[row] < 0:
                break  # fiches exclues par le filtre
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(scores[row]),
                    matched_terms=[
                        {"term": part["label"], "weight": round(float(1.0 - gaps[row, index]), 4)}
                        for index, part in enumerate(parts)
                    ],
                )
            )
        return results

    def _order(self, scores):
        """Indices triés : meilleur score d'abord, puis facilité, puis identifiant."""
        return np.lexsort((self.plant_ids, self.ease, -scores))

    def index_stats(self):
        if self.features is None:
            return None
        return {
            "documents": int(self.features.shape[0]),
            "dimensions": int(self.features.shape[1]),
            "letter_pairs": int(len(self.pairs)),
            "matrix_memory_kb": round(
                (
                    self.features.nbytes
                    + sum(
                        matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
                        for matrix in self.pair_matrices.values()
                    )
                )
                / 1024,
                1,
            ),
            "fit_duration_ms": round(self.fit_duration_ms, 2),
        }
