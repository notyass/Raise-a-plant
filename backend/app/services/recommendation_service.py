"""Orchestration d'une recommandation.

Ce service fait le lien entre la base (plant_service), l'algorithme
(recommenders) et les métriques (metrics_service). Les contrôleurs
n'appellent que lui.
"""
import threading
import time

from flask import current_app

from ..errors import ApiError
from . import metrics_service, plant_service
from .document_builder import build_document
from .query_builder import build_query_parts, build_query_text, clean_criteria
from .recommenders import APPROACHES, EmbeddingRecommender, PlantDocument, get_recommender_class

# Index gardés en mémoire : clé d'approche -> {"recommender", "corpus_size"}.
# Construire l'index coûte cher ; on ne le fait qu'une fois par processus.
_index_cache = {}
_index_lock = threading.Lock()


def reset_index_cache():
    """Oublie les index (utilisé par les tests et après un nouvel import)."""
    with _index_lock:
        _index_cache.clear()


def _unavailable_reason(recommender_class):
    """None si l'approche est utilisable, sinon la raison à afficher."""
    if recommender_class is EmbeddingRecommender and current_app.config.get("EMBEDDING_ENCODER"):
        return None  # un encodeur est fourni par la configuration (tests)
    return recommender_class.unavailable_reason()


def _create_recommender(recommender_class):
    """Crée une approche avec ses réglages, lus dans la configuration."""
    if recommender_class is EmbeddingRecommender:
        custom_encoder = current_app.config.get("EMBEDDING_ENCODER")
        return EmbeddingRecommender(
            model_name=current_app.config["EMBEDDING_MODEL"],
            encoder=custom_encoder,
            # Les vecteurs des fiches sont gardés dans le dossier « instance ».
            cache_dir=None if custom_encoder else current_app.instance_path,
        )
    return recommender_class()


def get_recommender(approach):
    """Renvoie l'approche demandée, index construit."""
    recommender_class = get_recommender_class(approach)

    reason = _unavailable_reason(recommender_class)
    if reason:
        raise ApiError(f"Approche indisponible : {reason}", status_code=503)

    corpus_size = plant_service.count_plants()
    if corpus_size == 0:
        raise ApiError(
            "La base ne contient aucune plante. Lance d'abord : flask --app run seed",
            status_code=503,
        )

    with _index_lock:
        entry = _index_cache.get(approach)
        # On reconstruit si le nombre de plantes a changé (nouvel import).
        if entry is None or entry["corpus_size"] != corpus_size:
            documents = [
                PlantDocument(plant_id=plant.id, text=build_document(plant))
                for plant in plant_service.get_all_plants()
            ]
            recommender = _create_recommender(recommender_class)
            recommender.fit(documents)
            entry = {"recommender": recommender, "corpus_size": corpus_size}
            _index_cache[approach] = entry
    return entry["recommender"]


def recommend(criteria, approach="tfidf", top_k=10):
    """Calcule une recommandation et renvoie la réponse de l'API."""
    total_start = time.perf_counter()

    cleaned = clean_criteria(criteria)

    # Catégorie : sert de filtre strict et ajoute son nom à la requête.
    category_name = None
    allowed_ids = None
    if "category" in cleaned:
        category = plant_service.get_category(cleaned["category"])
        if category is None:
            raise ApiError(f"Catégorie inconnue : {cleaned['category']!r}.")
        category_name = category.name
        allowed_ids = plant_service.get_plant_ids_by_category(category.slug)

    query_parts = build_query_parts(cleaned, category_name=category_name)
    query_text = build_query_text(cleaned, category_name=category_name)
    if not query_text:
        raise ApiError("Choisis au moins un critère pour obtenir une recommandation.")

    recommender = get_recommender(approach)
    corpus_size = _index_cache[approach]["corpus_size"]

    # On chronomètre uniquement le calcul de l'algorithme.
    algo_start = time.perf_counter()
    recommendations = recommender.recommend(
        query_text, top_k=top_k, allowed_ids=allowed_ids, query_parts=query_parts
    )
    algo_ms = (time.perf_counter() - algo_start) * 1000

    plants = plant_service.get_plants_by_ids([rec.plant_id for rec in recommendations])
    results = []
    for rank, rec in enumerate(recommendations, start=1):
        plant = plants.get(rec.plant_id)
        if plant is None:
            continue
        results.append(
            {
                "rank": rank,
                "score": round(rec.score, 4),
                "matched_terms": rec.matched_terms,
                "plant": plant.to_dict(),
            }
        )

    total_ms = (time.perf_counter() - total_start) * 1000
    run = metrics_service.record_run(
        approach=approach,
        algo_ms=algo_ms,
        total_ms=total_ms,
        result_count=len(results),
        corpus_size=corpus_size,
        query_text=query_text,
    )

    return {
        "run_id": run.id,
        "approach": {
            "key": recommender.key,
            "label": recommender.label,
            "explanation": recommender.explanation,
        },
        "criteria": cleaned,
        "query_text": query_text,
        "timing": {"algo_ms": round(algo_ms, 3), "total_ms": round(total_ms, 3)},
        "corpus_size": corpus_size,
        "count": len(results),
        "results": results,
    }


def describe_approaches():
    """Toutes les approches, avec leur disponibilité et les mesures de leur index."""
    approaches = []
    for key, recommender_class in APPROACHES.items():
        info = recommender_class.describe()
        reason = _unavailable_reason(recommender_class)
        info["available"] = reason is None
        info["unavailable_reason"] = reason
        entry = _index_cache.get(key)
        info["index"] = entry["recommender"].index_stats() if entry else None
        approaches.append(info)
    return approaches


def build_indexes():
    """Construit l'index de chaque approche disponible (commande build-index)."""
    built = []
    for key, recommender_class in APPROACHES.items():
        if _unavailable_reason(recommender_class) is None:
            built.append((key, get_recommender(key).index_stats()))
    return built
