"""Interface commune à toutes les approches de recommandation.

Chaque approche hérite de BaseRecommender et code trois méthodes :
  - fit(documents)      : prépare l'index, une seule fois ;
  - recommend(query...) : renvoie les plantes les plus proches de la requête ;
  - index_stats()       : mesures sur l'index, pour le tableau de bord.

Grâce à cette interface, les contrôleurs et le frontend traitent toutes les
approches de la même façon. Les approches ne connaissent ni Flask ni la base
de données : elles reçoivent des textes et renvoient des identifiants avec
un score.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PlantDocument:
    """Une plante vue par un algorithme : son identifiant et son texte."""

    plant_id: int
    text: str


@dataclass
class Recommendation:
    """Un résultat : la plante, son score et ce qui l'explique."""

    plant_id: int
    score: float
    matched_terms: list = field(default_factory=list)


class BaseRecommender(ABC):
    key = ""  # identifiant technique, ex. "tfidf"
    label = ""  # nom affiché dans l'interface
    description = ""
    explanation = ""  # phrase affichée sous « Pourquoi cette plante ? »
    complexity = {}  # complexité théorique, affichée dans le tableau de bord

    @abstractmethod
    def fit(self, documents):
        """Construit l'index à partir d'une liste de PlantDocument."""

    @abstractmethod
    def recommend(self, query_text, top_k=10, allowed_ids=None, query_parts=None):
        """Renvoie au plus top_k Recommendation, de la plus à la moins proche.

        query_text  : la requête complète, ex. "full sun easy".
        allowed_ids : ensemble d'identifiants autorisés (filtre), ou None.
        query_parts : la même requête découpée par critère, sous la forme
                      [{"label": "Plein soleil", "text": "full sun"}, ...].
                      Sert aux approches qui expliquent critère par critère.
        """

    @abstractmethod
    def index_stats(self):
        """Renvoie des mesures sur l'index (taille, temps de construction...)."""

    @classmethod
    def unavailable_reason(cls):
        """Renvoie None si l'approche est utilisable, sinon la raison."""
        return None

    @classmethod
    def describe(cls):
        return {
            "key": cls.key,
            "label": cls.label,
            "description": cls.description,
            "explanation": cls.explanation,
            "complexity": cls.complexity,
        }
