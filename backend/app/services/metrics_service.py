"""Métriques de performance : enregistrement et statistiques des temps de réponse."""
import statistics
from collections import defaultdict

from ..extensions import db
from ..models import RecommendationRun

# Nombre de mesures récentes renvoyées pour tracer la courbe.
HISTORY_SIZE = 50


def record_run(approach, algo_ms, total_ms, result_count, corpus_size, query_text):
    """Enregistre une recommandation dans le journal et renvoie la ligne créée."""
    run = RecommendationRun(
        approach=approach,
        algo_ms=algo_ms,
        total_ms=total_ms,
        result_count=result_count,
        corpus_size=corpus_size,
        query_text=query_text,
    )
    db.session.add(run)
    db.session.commit()
    return run


def fetch_runs():
    """Toutes les recommandations enregistrées, de la plus ancienne à la plus récente."""
    statement = db.select(RecommendationRun).order_by(RecommendationRun.id)
    return db.session.scalars(statement).all()


def compute_stats(values):
    """Statistiques d'une liste de durées en millisecondes.

    Fonction pure (pas de base de données) : facile à tester.
    """
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "p95": None}

    ordered = sorted(values)
    # 95e centile : valeur sous laquelle se trouvent 95 % des mesures.
    p95_index = max(0, -(-95 * len(ordered) // 100) - 1)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
        "mean": round(statistics.fmean(ordered), 3),
        "median": round(statistics.median(ordered), 3),
        "p95": round(ordered[p95_index], 3),
    }


def get_metrics():
    """Statistiques par approche : {clé d'approche: {...}}."""
    runs_by_approach = defaultdict(list)
    for run in fetch_runs():
        runs_by_approach[run.approach].append(run)

    metrics = {}
    for approach, runs in runs_by_approach.items():
        metrics[approach] = {
            "algo_ms": compute_stats([run.algo_ms for run in runs]),
            "total_ms": compute_stats([run.total_ms for run in runs]),
            "history": [
                {
                    "run_id": run.id,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "algo_ms": round(run.algo_ms, 3),
                    "total_ms": round(run.total_ms, 3),
                    "result_count": run.result_count,
                }
                for run in runs[-HISTORY_SIZE:]
            ],
        }
    return metrics
