import threading
import time

from app.errors import ApiError
from app.services.MetricsService import MetricsService
from app.services.PlantService import PlantService
from app.services.document_builder import build_attributes, build_names
from app.services.query_builder import build_query_parts, clean_criteria, describe_query
from app.services.recommenders import (
    APPROACHES,
    DEFAULT_APPROACH,
    OBJECTIVE_CARE,
    OBJECTIVE_ENVIRONMENT,
    PlantDocument,
    get_recommender_class,
)
from app.services.text_utils import simplify

MAX_QUERY_LENGTH = 80

# Index gardés en mémoire : clé de méthode -> {"recommender", "corpus_size"}.
# Construire un index coûte cher ; on ne le fait qu'une fois par processus,
# alors qu'un service est recréé à chaque requête.
_index_cache = {}
_index_lock = threading.Lock()


def reset_index_cache():
    """Oublie les index (utilisé par les tests et après un nouvel import)."""
    with _index_lock:
        _index_cache.clear()


class RecommendationService:
    """Service de recommandation : fait le lien entre les plantes
    (PlantService), les méthodes (recommenders) et les métriques (MetricsService)."""

    def __init__(self, db_uri=None):
        self.ps = PlantService(db_uri=db_uri)
        self.ms = MetricsService(db_uri=db_uri)

    def getRecommender(self, approach):
        """retourne (méthode avec son index construit, nombre de fiches indexées)"""
        recommender_class = get_recommender_class(approach)

        corpus_size = self.ps.countPlants()
        if corpus_size == 0:
            raise ApiError(
                "La base ne contient aucune plante. Lance d'abord : python prepa_db.py",
                status_code=503,
            )

        with _index_lock:
            entry = _index_cache.get(approach)
            # on reconstruit si le nombre de plantes a changé (nouvel import)
            if entry is None or entry['corpus_size'] != corpus_size:
                documents = [
                    PlantDocument(
                        plant_id=plant.id,
                        names=build_names(plant),
                        attributes=build_attributes(plant),
                    )
                    for plant in self.ps.getAllPlants()
                ]
                recommender = recommender_class()
                recommender.fit(documents)
                entry = {'recommender': recommender, 'corpus_size': corpus_size}
                _index_cache[approach] = entry
        return entry['recommender'], entry['corpus_size']

    def search(self, query, approach=DEFAULT_APPROACH, top_k=10):
        """O1 : retrouve une plante à partir de son nom"""
        total_start = time.perf_counter()

        if not isinstance(query, str) or not query.strip():
            raise ApiError("Écris le nom d'une plante.")
        query = query.strip()[:MAX_QUERY_LENGTH]

        recommender, corpus_size = self.getRecommender(approach)

        # on chronomètre uniquement le calcul de la méthode
        algo_start = time.perf_counter()
        recommendations = recommender.search(simplify(query), top_k=top_k)
        algo_ms = (time.perf_counter() - algo_start) * 1000

        return self._buildResponse(
            OBJECTIVE_CARE, recommender, recommendations, query, {'query': query},
            corpus_size, algo_ms, total_start,
        )

    def recommend(self, criteria, approach=DEFAULT_APPROACH, top_k=10):
        """O2 : propose des plantes pour un environnement"""
        total_start = time.perf_counter()

        cleaned = clean_criteria(criteria)

        # catégorie : sert de filtre strict pour les deux méthodes
        category_part = None
        allowed_ids = None
        if 'category' in cleaned:
            category = self.ps.getCategoryBySlug(cleaned['category'])
            if category is None:
                raise ApiError(f"Catégorie inconnue : {cleaned['category']!r}.")
            category_part = {'slug': category.slug, 'label': category.name}
            allowed_ids = self.ps.getPlantIdsByCategory(category.slug)

        # les deux méthodes reçoivent exactement la même demande
        query_parts = build_query_parts(cleaned, category=category_part)
        if not query_parts:
            raise ApiError("Choisis au moins un critère pour obtenir une recommandation.")

        recommender, corpus_size = self.getRecommender(approach)

        # on chronomètre uniquement le calcul de la méthode
        algo_start = time.perf_counter()
        recommendations = recommender.recommend(query_parts, top_k=top_k, allowed_ids=allowed_ids)
        algo_ms = (time.perf_counter() - algo_start) * 1000

        return self._buildResponse(
            OBJECTIVE_ENVIRONMENT, recommender, recommendations, describe_query(query_parts),
            cleaned, corpus_size, algo_ms, total_start,
        )

    def _buildResponse(self, objective, recommender, recommendations, query_text, criteria,
                       corpus_size, algo_ms, total_start):
        """ajoute les fiches aux résultats, enregistre la mesure et construit la réponse de l'API"""
        plants = self.ps.getPlantsByIds([rec.plant_id for rec in recommendations])
        results = []
        for rank, rec in enumerate(recommendations, start=1):
            plant = plants.get(rec.plant_id)
            if plant is None:
                continue
            results.append({
                'rank': rank,
                'score': round(rec.score, 4),
                'matched_terms': rec.matched_terms,
                'plant': PlantService.describePlant(plant),
            })

        total_ms = (time.perf_counter() - total_start) * 1000
        run = self.ms.recordRun(
            approach=recommender.key,
            objective=objective,
            algo_ms=algo_ms,
            total_ms=total_ms,
            result_count=len(results),
            corpus_size=corpus_size,
            query_text=query_text,
        )

        return {
            'run_id': run.id,
            'objective': objective,
            'approach': {
                'key': recommender.key,
                'label': recommender.label,
                'explanation': recommender.explanations.get(objective, ''),
            },
            'criteria': criteria,
            'query_text': query_text,
            'timing': {'algo_ms': round(algo_ms, 3), 'total_ms': round(total_ms, 3)},
            'corpus_size': corpus_size,
            'count': len(results),
            'results': results,
        }

    def describeApproaches(self):
        """les méthodes, avec les mesures de leur index"""
        approaches = []
        for key, recommender_class in APPROACHES.items():
            info = recommender_class.describe()
            entry = _index_cache.get(key)
            info['index'] = entry['recommender'].index_stats() if entry else None
            approaches.append(info)
        return approaches
