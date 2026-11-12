"""Méthode n°1, heuristique : des règles logiques « SI... ALORS... ».

Idée : pas de calcul savant, seulement des règles écrites à la main.

  - O2 (plantes pour un environnement) : chaque critère est un filtre
    strict. SI la fiche ne respecte pas un critère ALORS elle est éliminée.
    Une plante de plein soleil ne sera jamais proposée pour un coin d'ombre.
    Les fiches restantes sont classées par précision.
  - O1 (retrouver une plante) : des règles sur le nom, de la plus exigeante
    à la plus souple (nom exact, début du nom, mot du nom, type, nom latin).

Cette méthode est rapide et entièrement explicable, mais rigide : une faute
de frappe ou un critère trop strict, et elle ne renvoie rien.
"""
import time

import numpy as np

from app.services.query_builder import WEIGHTS
from app.services.recommenders.base import BaseRecommender, Recommendation, ease_rank

# Points d'un critère respecté (O2) :
SCORE_EXACT = 1.0  # la fiche ne mentionne que la valeur demandée
SCORE_COMPATIBLE = 0.75  # la fiche accepte la valeur demandée parmi d'autres

# Critères dont la fiche porte une liste de codes.
CODE_KEYS = ("sun", "water", "soil", "season", "difficulty")

MIN_QUERY_LENGTH = 2


class HeuristicRecommender(BaseRecommender):
    key = "heuristic"
    label = "Heuristique (règles SI... ALORS)"
    description = (
        "Des règles logiques écrites à la main. Pour un environnement, chaque "
        "critère est un filtre strict : une fiche qui n'en respecte pas un est "
        "éliminée. Pour un nom, on cherche une correspondance exacte de lettres."
    )
    explanations = {
        "care": "Règle qui a retenu cette fiche (plus la règle est exigeante, plus le score est haut).",
        "environment": (
            "Tous les critères sont respectés. Points de chacun : ils sont plus "
            "élevés quand la fiche ne mentionne que la valeur demandée."
        ),
    }
    complexity = {
        "notation": "N = nombre de fiches, c = nombre de critères choisis (7 au plus)",
        "indexation": "O(N) : simple copie des noms et des caractéristiques, au premier appel",
        "recherche": "O(N) comparaisons de textes + O(N log N) pour le tri",
        "recommandation": "O(N × c) tests de règles + O(N log N) pour le tri",
        "memoire": "O(N)",
        "pistes": (
            "Faire les filtres en SQL (WHERE) pour ne lire que les fiches utiles ; "
            "remplacer la boucle Python par des tableaux numpy ; ne garder que "
            "les k meilleures sans trier les N scores."
        ),
    }

    def __init__(self):
        self.plant_ids = np.array([], dtype=int)
        self.names = []  # noms simplifiés de chaque fiche (O1)
        self.attributes = []  # caractéristiques normalisées de chaque fiche (O2)
        self.ease = np.array([], dtype=int)  # rang de facilité, pour départager
        self.fit_duration_ms = None

    def fit(self, documents):
        start = time.perf_counter()
        self.plant_ids = np.array([doc.plant_id for doc in documents], dtype=int)
        self.names = [doc.names for doc in documents]
        self.attributes = [doc.attributes for doc in documents]
        self.ease = np.array([ease_rank(doc.attributes) for doc in documents], dtype=int)
        self.fit_duration_ms = (time.perf_counter() - start) * 1000

    # ----- O1 : retrouver une plante par son nom -----

    @staticmethod
    def _search_rule(query, names):
        """Applique les règles dans l'ordre et renvoie (score, raison).

        La première règle vraie l'emporte. Aucune règle vraie : (0, None).
        """
        name = names["name"]
        if name == query:
            return 1.0, "Le nom est exactement celui recherché"
        if name.startswith(query):
            return 0.9, "Le nom commence par la recherche"
        if any(word.startswith(query) for word in name.split()):
            return 0.8, "Un mot du nom commence par la recherche"
        if query in name:
            return 0.7, "Le nom contient la recherche"
        for category in names["categories"]:
            if any(word.startswith(query) for word in category.split()):
                return 0.6, "Le type de plante correspond à la recherche"
        if query in names["scientific_name"]:
            return 0.5, "Le nom latin contient la recherche"
        return 0.0, None

    def search(self, query, top_k=10):
        if len(query) < MIN_QUERY_LENGTH:
            return []

        scores = np.zeros(len(self.plant_ids))
        reasons = [None] * len(self.plant_ids)
        for row, names in enumerate(self.names):
            scores[row], reasons[row] = self._search_rule(query, names)

        results = []
        for row in self._order(scores)[:top_k]:
            if scores[row] <= 0:
                break  # les suivantes ne respectent aucune règle
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(scores[row]),
                    matched_terms=[{"term": reasons[row], "weight": float(scores[row])}],
                )
            )
        return results

    # ----- O2 : plantes pour un environnement -----

    @staticmethod
    def _criterion_score(part, attributes):
        """Points (0, 0,75 ou 1) d'une fiche pour un critère de la demande."""
        key = part["key"]

        if key in CODE_KEYS:
            codes = attributes.get(key, [])
            if part["code"] not in codes:
                return 0.0
            return SCORE_EXACT if len(codes) == 1 else SCORE_COMPATIBLE

        if key == "category":
            return SCORE_EXACT if attributes.get("category") == part["code"] else 0.0

        if key == "container":
            return SCORE_EXACT if attributes.get("container") else 0.0

        return 0.0

    def _score(self, parts, total_weight, attributes):
        """Score d'une fiche, ou 0 si une règle l'élimine."""
        points = 0.0
        for part in parts:
            criterion_score = self._criterion_score(part, attributes)
            if criterion_score == 0:
                return 0.0  # SI un critère n'est pas respecté ALORS la fiche est éliminée
            points += WEIGHTS[part["key"]] * criterion_score
        return points / total_weight

    def recommend(self, query_parts, top_k=10, allowed_ids=None):
        parts = [part for part in query_parts if part["key"] in WEIGHTS]
        if not parts:
            return []
        total_weight = sum(WEIGHTS[part["key"]] for part in parts)

        # 1. Filtres stricts puis score de précision pour chaque fiche.
        scores = np.zeros(len(self.plant_ids))
        for row, attributes in enumerate(self.attributes):
            scores[row] = self._score(parts, total_weight, attributes)

        # 2. Filtre optionnel sur les identifiants (une seule catégorie).
        if allowed_ids is not None:
            allowed = np.isin(self.plant_ids, list(allowed_ids))
            scores = np.where(allowed, scores, 0.0)

        # 3. Classement des fiches restantes.
        results = []
        for row in self._order(scores)[:top_k]:
            if scores[row] <= 0:
                break  # fiches éliminées
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(scores[row]),
                    matched_terms=self._explain(parts, total_weight, row),
                )
            )
        return results

    def _order(self, scores):
        """Indices triés : meilleur score d'abord. Beaucoup de fiches ont le
        même score ; on départage par facilité de culture, puis par identifiant
        pour un ordre toujours identique."""
        return np.lexsort((self.plant_ids, self.ease, -scores))

    def _explain(self, parts, total_weight, row):
        """Détail du score : les points apportés par chaque critère."""
        details = []
        for part in parts:
            points = WEIGHTS[part["key"]] * self._criterion_score(part, self.attributes[row])
            details.append({"term": part["label"], "weight": round(points / total_weight, 4)})
        details.sort(key=lambda item: -item["weight"])
        return details

    def index_stats(self):
        if self.fit_duration_ms is None:
            return None
        return {
            "documents": int(len(self.plant_ids)),
            "weighted_criteria": len(WEIGHTS),
            "fit_duration_ms": round(self.fit_duration_ms, 2),
        }
