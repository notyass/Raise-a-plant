import statistics
from collections import defaultdict

from flask import current_app

from app.models.RecommendationRunDAO import RecommendationRunORM as RecommendationRunDAO

# Nombre de mesures récentes renvoyées pour tracer la courbe.
HISTORY_SIZE = 50


class MetricsService:
    """Service des métriques de performance : enregistrement et statistiques."""

    def __init__(self, db_uri=None):
        if db_uri is None:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        self.rdao = RecommendationRunDAO(db_uri=db_uri)

    def recordRun(self, approach, objective, algo_ms, total_ms, result_count, corpus_size, query_text):
        """enregistre une recherche dans le journal"""
        return self.rdao.add(
            approach, objective, algo_ms, total_ms, result_count, corpus_size, query_text
        )

    def getMetrics(self):
        """statistiques par méthode et par objectif :
        {clé de méthode: {clé d'objectif: {'algo_ms', 'total_ms', 'empty_count', 'history'}}}"""
        groups = defaultdict(list)
        for run in self.rdao.findAll():
            groups[(run.approach, run.objective)].append(run)

        metrics = defaultdict(dict)
        for (approach, objective), runs in groups.items():
            metrics[approach][objective] = {
                'algo_ms': MetricsService.computeStats([run.algo_ms for run in runs]),
                'total_ms': MetricsService.computeStats([run.total_ms for run in runs]),
                # recherches qui n'ont renvoyé aucun résultat
                'empty_count': sum(1 for run in runs if run.result_count == 0),
                'history': [
                    {
                        'run_id': run.id,
                        'created_at': run.created_at.isoformat() if run.created_at else None,
                        'algo_ms': round(run.algo_ms, 3),
                        'total_ms': round(run.total_ms, 3),
                        'result_count': run.result_count,
                    }
                    for run in runs[-HISTORY_SIZE:]
                ],
            }
        return dict(metrics)

    @staticmethod
    def emptyMetrics():
        """mesures d'une méthode qui n'a pas encore été utilisée pour un objectif"""
        stats = MetricsService.computeStats([])
        return {'algo_ms': stats, 'total_ms': stats, 'empty_count': 0, 'history': []}

    @staticmethod
    def computeStats(values):
        """statistiques d'une liste de durées en millisecondes
        (méthode statique sans base de données : facile à tester)"""
        if not values:
            return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None, 'p95': None}

        ordered = sorted(values)
        # 95e centile : valeur sous laquelle se trouvent 95 % des mesures.
        p95_index = max(0, -(-95 * len(ordered) // 100) - 1)
        return {
            'count': len(ordered),
            'min': round(ordered[0], 3),
            'max': round(ordered[-1], 3),
            'mean': round(statistics.fmean(ordered), 3),
            'median': round(statistics.median(ordered), 3),
            'p95': round(ordered[p95_index], 3),
        }
