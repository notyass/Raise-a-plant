"""Approches de recommandation et registre des approches."""
from ...errors import ApiError
from .base import BaseRecommender, PlantDocument, Recommendation
from .embeddings import EmbeddingRecommender
from .tfidf import TfidfRecommender

# Registre : clé -> classe. Pour ajouter une approche, il suffit de créer une
# classe qui hérite de BaseRecommender et de l'ajouter ici.
APPROACHES = {
    TfidfRecommender.key: TfidfRecommender,
    EmbeddingRecommender.key: EmbeddingRecommender,
}


def get_recommender_class(key):
    if key not in APPROACHES:
        raise ApiError(
            f"Approche inconnue : {key!r}. Approches possibles : {', '.join(APPROACHES)}."
        )
    return APPROACHES[key]


__all__ = [
    "APPROACHES",
    "BaseRecommender",
    "EmbeddingRecommender",
    "PlantDocument",
    "Recommendation",
    "TfidfRecommender",
    "get_recommender_class",
]
