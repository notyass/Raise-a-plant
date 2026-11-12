"""Route du tableau de bord : métriques de performance par approche."""
from flask import Blueprint, jsonify

from ..services import metrics_service, plant_service, recommendation_service

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.get("/metrics")
def get_metrics():
    metrics = metrics_service.get_metrics()
    empty = metrics_service.compute_stats([])

    approaches = []
    for approach in recommendation_service.describe_approaches():
        measured = metrics.get(approach["key"], {})
        approach["algo_ms"] = measured.get("algo_ms", empty)
        approach["total_ms"] = measured.get("total_ms", empty)
        approach["history"] = measured.get("history", [])
        approaches.append(approach)

    return jsonify({"corpus_size": plant_service.count_plants(), "approaches": approaches})
