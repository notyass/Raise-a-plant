"""Méthodes de recommandation et registre des méthodes."""
from app.errors import ApiError
from app.services.recommenders.base import (
    OBJECTIVE_CARE,
    OBJECTIVE_ENVIRONMENT,
    OBJECTIVES,
    BaseRecommender,
    PlantDocument,
    Recommendation,
)
from app.services.recommenders.heuristic import HeuristicRecommender
from app.services.recommenders.vector import VectorRecommender

# Registre : clé -> classe, dans l'ordre d'affichage. Pour ajouter une
# méthode, il suffit de créer une classe qui hérite de BaseRecommender et de
# l'ajouter ici.
APPROACHES = {
    HeuristicRecommender.key: HeuristicRecommender,  # méthode n°1
    VectorRecommender.key: VectorRecommender,  # méthode n°2
}
DEFAULT_APPROACH = HeuristicRecommender.key


def get_recommender_class(key):
    if key not in APPROACHES:
        raise ApiError(
            f"Méthode inconnue : {key!r}. Méthodes possibles : {', '.join(APPROACHES)}."
        )
    return APPROACHES[key]


__all__ = [
    'APPROACHES',
    'DEFAULT_APPROACH',
    'OBJECTIVES',
    'OBJECTIVE_CARE',
    'OBJECTIVE_ENVIRONMENT',
    'BaseRecommender',
    'HeuristicRecommender',
    'PlantDocument',
    'Recommendation',
    'VectorRecommender',
    'get_recommender_class',
]
