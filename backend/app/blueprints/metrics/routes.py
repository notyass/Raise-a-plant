from flask import Blueprint, jsonify

from app.services.MetricsService import MetricsService
from app.services.PlantService import PlantService
from app.services.RecommendationService import RecommendationService
from app.services.recommenders import OBJECTIVES

metrics_bp = Blueprint('metrics', __name__)


@metrics_bp.route('/metrics', methods=['GET'])
def metrics():
    """tableau de bord : métriques de chaque méthode, pour chaque objectif"""
    ps = PlantService()
    ms = MetricsService()
    rs = RecommendationService()

    measured = ms.getMetrics()

    approaches = []
    for approach in rs.describeApproaches():
        approach['objectives'] = {
            objective: measured.get(approach['key'], {}).get(objective, MetricsService.emptyMetrics())
            for objective in OBJECTIVES
        }
        approaches.append(approach)

    return jsonify({
        'corpus_size': ps.countPlants(),
        'objectives': OBJECTIVES,
        'approaches': approaches,
    })
