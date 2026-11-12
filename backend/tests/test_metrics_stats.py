"""Tests du calcul des statistiques de temps de réponse."""
from app.services.MetricsService import MetricsService

compute_stats = MetricsService.computeStats


def test_empty_list():
    stats = compute_stats([])
    assert stats["count"] == 0
    assert stats["mean"] is None


def test_min_max_mean_median():
    stats = compute_stats([4.0, 1.0, 3.0, 2.0])
    assert stats["count"] == 4
    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
    assert stats["mean"] == 2.5
    assert stats["median"] == 2.5


def test_p95_ignores_the_slowest_5_percent():
    values = [float(value) for value in range(1, 101)]  # 1 à 100
    assert compute_stats(values)["p95"] == 95.0


def test_single_value():
    stats = compute_stats([7.5])
    assert stats["min"] == stats["max"] == stats["mean"] == stats["median"] == stats["p95"] == 7.5
