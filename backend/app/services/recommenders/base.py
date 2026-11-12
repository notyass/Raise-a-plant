"""Interface commune aux deux méthodes de recommandation.

Chaque méthode hérite de BaseRecommender et répond aux deux objectifs :
  - search(query)          : O1, retrouver une plante à partir de son nom ;
  - recommend(query_parts) : O2, proposer des plantes pour un environnement.
Elle code aussi fit(documents), qui prépare son index une seule fois, et
index_stats(), qui renvoie des mesures pour le tableau de bord.

Grâce à cette interface, les services et le frontend traitent les deux
méthodes de la même façon. Les méthodes ne connaissent ni Flask ni la base
de données : elles reçoivent des PlantDocument et renvoient des
identifiants avec un score.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Les deux objectifs de l'application.
OBJECTIVE_CARE = "care"  # O1 : prendre soin d'une plante donnée
OBJECTIVE_ENVIRONMENT = "environment"  # O2 : plantes pour un environnement donné
OBJECTIVES = {
    OBJECTIVE_CARE: "O1 : trouver une plante pour savoir en prendre soin",
    OBJECTIVE_ENVIRONMENT: "O2 : trouver les plantes adaptées à un environnement",
}


@dataclass
class PlantDocument:
    """Une plante vue par une méthode (voir services/document_builder.py)."""

    plant_id: int
    names: dict  # {"name", "scientific_name", "categories"}, textes simplifiés
    attributes: dict  # {"category", "sun", "water", "soil", "season", "difficulty", "container"}


@dataclass
class Recommendation:
    """Un résultat : la plante, son score et ce qui l'explique."""

    plant_id: int
    score: float
    matched_terms: list = field(default_factory=list)


def ease_rank(attributes):
    """Rang de facilité d'une plante : 0 = facile ... 3 = difficile ou inconnu.

    Sert aux deux méthodes pour départager les fiches de même score :
    l'application vise les débutants, les plus faciles passent devant.
    """
    codes = attributes.get("difficulty", [])
    if codes == ["easy"]:
        return 0
    if "easy" in codes:
        return 1
    if codes == ["moderate"]:
        return 2
    return 3


class BaseRecommender(ABC):
    key = ""  # identifiant technique, ex. "heuristic"
    label = ""  # nom affiché dans l'interface
    description = ""
    explanations = {}  # phrase affichée sous « Pourquoi ce résultat ? », par objectif
    complexity = {}  # complexité théorique, affichée dans le tableau de bord

    @abstractmethod
    def fit(self, documents):
        """Construit l'index à partir d'une liste de PlantDocument."""

    @abstractmethod
    def search(self, query, top_k=10):
        """O1 : renvoie au plus top_k Recommendation pour un nom de plante.

        query : le texte tapé, déjà simplifié (minuscules, sans accents).
        """

    @abstractmethod
    def recommend(self, query_parts, top_k=10, allowed_ids=None):
        """O2 : renvoie au plus top_k Recommendation pour un environnement.

        query_parts : la demande découpée par critère
                      (voir query_builder.build_query_parts).
        allowed_ids : ensemble d'identifiants autorisés (filtre), ou None.
        """

    @abstractmethod
    def index_stats(self):
        """Renvoie des mesures sur l'index (taille, temps de construction...)."""

    @classmethod
    def describe(cls):
        return {
            "key": cls.key,
            "label": cls.label,
            "description": cls.description,
            "explanations": cls.explanations,
            "complexity": cls.complexity,
        }
