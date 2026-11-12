"""Approche n°1 : TF-IDF + similarité cosinus (filtrage basé sur le contenu).

Idée : un mot compte beaucoup pour une fiche s'il y est fréquent (TF, « term
frequency ») et s'il est rare dans l'ensemble des fiches (IDF, « inverse
document frequency »). Chaque fiche devient un vecteur de poids TF-IDF, la
requête aussi, et on classe les fiches selon l'angle entre leur vecteur et
celui de la requête (similarité cosinus : 1 = même direction, 0 = aucun mot
en commun).
"""
import re
import time

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .base import BaseRecommender, Recommendation

# Nombre de termes affichés pour expliquer un résultat.
MAX_EXPLANATION_TERMS = 5

# Mots vides anglais (« the », « and », « of »...) ignorés. La liste de
# scikit-learn contient « full » et « well », utiles en jardinage
# (« full sun », « well drained ») : on les garde.
STOP_WORDS = ENGLISH_STOP_WORDS - {"full", "well"}
SEGMENT_SEPARATOR = re.compile(r"[.,;:!?()\n—–]+")
WORD = re.compile(r"[a-z0-9]+")


def analyze(text):
    """Découpe un texte en termes : les mots seuls et les paires de mots voisins.

    Les paires ne traversent pas la ponctuation : dans « Full sun. Easy. »,
    on obtient « full sun » mais pas « sun easy », qui ne voudrait rien dire.
    """
    terms = []
    for segment in SEGMENT_SEPARATOR.split(text.lower()):
        words = [
            word for word in WORD.findall(segment) if len(word) > 1 and word not in STOP_WORDS
        ]
        terms.extend(words)
        terms.extend(f"{first} {second}" for first, second in zip(words, words[1:]))
    return terms


class TfidfRecommender(BaseRecommender):
    key = "tfidf"
    label = "TF-IDF + cosinus"
    description = (
        "Chaque fiche est représentée par les poids TF-IDF de ses mots. "
        "On classe les fiches par similarité cosinus avec la requête."
    )
    explanation = "Mots de ta demande retrouvés dans sa fiche, avec leur part dans le score."
    complexity = {
        "notation": (
            "N = nombre de fiches, L = nombre moyen de termes distincts par "
            "fiche, V = taille du vocabulaire"
        ),
        "indexation": "O(N × L), une seule fois au premier appel",
        "requete": "O(N × L) pour le produit matrice-vecteur + O(N log N) pour le tri complet",
        "memoire": "O(N × L) pour la matrice creuse + O(V) pour le vocabulaire",
        "pistes": (
            "Index inversé pour ne parcourir que les fiches contenant un terme "
            "de la requête ; sélection des k meilleurs sans trier les N scores."
        ),
    }

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer=analyze,  # notre découpage en termes (voir plus haut)
            sublinear_tf=True,  # 1 + log(tf) : répéter un mot 10 fois ne compte pas 10 fois
        )
        self.matrix = None  # matrice creuse N × V, lignes normalisées (norme 1)
        self.plant_ids = np.array([], dtype=int)
        self.terms = np.array([])
        self.fit_duration_ms = None

    def fit(self, documents):
        start = time.perf_counter()
        self.plant_ids = np.array([doc.plant_id for doc in documents], dtype=int)
        self.matrix = self.vectorizer.fit_transform([doc.text for doc in documents])
        self.terms = self.vectorizer.get_feature_names_out()
        self.fit_duration_ms = (time.perf_counter() - start) * 1000

    def recommend(self, query_text, top_k=10, allowed_ids=None, query_parts=None):
        # query_parts n'est pas utilisé ici : TF-IDF explique par les mots communs.
        if self.matrix is None:
            raise RuntimeError("L'index n'est pas construit : appeler fit() d'abord.")

        # 1. La requête devient un vecteur dans le même espace que les fiches.
        query_vector = self.vectorizer.transform([query_text])
        if query_vector.nnz == 0:
            return []  # aucun mot de la requête n'existe dans le vocabulaire

        # 2. Similarité cosinus. Les vecteurs sont déjà de norme 1, donc le
        #    cosinus se réduit à un produit scalaire : une multiplication
        #    matrice × vecteur donne les N scores d'un coup.
        scores = (self.matrix @ query_vector.T).toarray().ravel()

        # 3. Filtre optionnel (ex. une seule catégorie).
        if allowed_ids is not None:
            allowed = np.isin(self.plant_ids, list(allowed_ids))
            scores = np.where(allowed, scores, 0.0)

        # 4. Tri de tous les scores, du plus grand au plus petit (V1, non optimisé).
        order = np.argsort(-scores, kind="stable")

        results = []
        for row in order[:top_k]:
            if scores[row] <= 0:
                break  # les suivants n'ont aucun terme en commun avec la requête
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(scores[row]),
                    matched_terms=self._explain(query_vector, row),
                )
            )
        return results

    def _explain(self, query_vector, row):
        """Termes communs à la requête et à la fiche, avec leur contribution.

        Le score est la somme, sur les termes communs, de
        (poids dans la requête × poids dans la fiche). On renvoie les termes
        qui contribuent le plus : c'est le « pourquoi » de la recommandation.
        """
        contributions = query_vector.multiply(self.matrix[row]).tocoo()
        weights = {
            str(self.terms[column]): float(weight)
            for column, weight in zip(contributions.col, contributions.data)
        }

        # « full » et « sun » n'apportent rien si « full sun » est déjà présent :
        # on retire les mots seuls qui font partie d'une paire trouvée.
        words_in_pairs = {word for term in weights if " " in term for word in term.split()}
        kept = [
            (term, weight)
            for term, weight in weights.items()
            if " " in term or term not in words_in_pairs
        ]
        kept.sort(key=lambda pair: -pair[1])

        return [
            {"term": term, "weight": round(weight, 4)}
            for term, weight in kept[:MAX_EXPLANATION_TERMS]
        ]

    def index_stats(self):
        if self.matrix is None:
            return None
        matrix = self.matrix
        memory_bytes = matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
        return {
            "documents": int(matrix.shape[0]),
            "vocabulary_size": int(matrix.shape[1]),
            "non_zero_values": int(matrix.nnz),
            "avg_terms_per_document": round(matrix.nnz / max(1, matrix.shape[0]), 1),
            "matrix_memory_kb": round(memory_bytes / 1024, 1),
            "fit_duration_ms": round(self.fit_duration_ms, 2),
        }
