"""Tests de la méthode vectorielle seule (sans Flask ni base de données)."""
import pytest

from app.services.query_builder import build_query_parts, clean_criteria
from app.services.recommenders import VectorRecommender

from .test_heuristic import DOCUMENTS


def make_recommender():
    recommender = VectorRecommender()
    recommender.fit(DOCUMENTS)
    return recommender


def recommend(criteria, **options):
    parts = build_query_parts(clean_criteria(criteria))
    return make_recommender().recommend(parts, **options)


def search(query, **options):
    return make_recommender().search(query, **options)


# ----- O2 : plantes pour un environnement -----

def test_identical_point_has_score_one():
    result = recommend({"sun": 100, "water": 0})[0]
    assert result.plant_id == 3  # romarin : plein soleil (1) et peu d'eau (0)
    assert result.score == pytest.approx(1.0)


def test_score_is_one_minus_the_weighted_distance():
    # tomate : soleil 1, eau 1. Demande : soleil 1, eau 0,5.
    # écarts 0 et 0,5, poids 3 et 3 : distance = racine((0² × 3 + 0,5² × 3) / 6) = 0,3536
    score = {r.plant_id: r.score for r in recommend({"sun": 100, "water": 50})}[1]
    assert score == pytest.approx(1 - 0.3536, abs=1e-4)


def test_every_plant_gets_a_score_even_far_from_the_request():
    # différence avec l'heuristique : aucune fiche n'est éliminée
    results = recommend({"sun": 0, "water": 0})
    assert len(results) == 4
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_slider_value_matters_inside_a_level():
    # 70 % et 100 % désignent tous deux « plein soleil », mais pas le même point
    at_70 = {r.plant_id: r.score for r in recommend({"sun": 70})}
    at_100 = {r.plant_id: r.score for r in recommend({"sun": 100})}
    assert at_70[2] > at_100[2]  # la laitue (soleil 0,75) est plus proche de 70 %


def test_binary_criteria():
    scores = {r.plant_id: r.score for r in recommend({"season": "cool", "container": True})}
    assert scores[2] == pytest.approx(1.0)  # laitue : saison fraîche et pot
    assert scores[4] < scores[2]  # carotte : saison fraîche mais pas en pot


def test_allowed_ids_and_top_k():
    assert sorted(r.plant_id for r in recommend({"sun": 100}, allowed_ids={2, 4})) == [2, 4]
    assert len(recommend({"sun": 100}, top_k=2)) == 2


def test_no_criteria_gives_no_result():
    assert make_recommender().recommend([]) == []


def test_explanation_gives_the_closeness_for_each_criterion():
    result = next(r for r in recommend({"sun": 100, "water": 50}) if r.plant_id == 1)
    assert result.matched_terms == [
        {"term": "Lumière : plein soleil (100 %)", "weight": 1.0},
        {"term": "Eau : arrosage modéré (50 %)", "weight": 0.5},
    ]


# ----- O1 : retrouver une plante par son nom -----

def test_search_exact_name_has_score_one():
    result = search("rosemary")[0]
    assert result.plant_id == 3
    assert result.score == pytest.approx(1.0)


def test_search_tolerates_typos():
    assert search("rosemarry")[0].plant_id == 3
    assert search("carot")[0].plant_id == 4


def test_search_also_compares_the_type_and_the_latin_name():
    assert search("tomate")[0].plant_id == 1  # type « tomates »
    assert search("lactuca sativa")[0].plant_id == 2  # nom latin


def test_search_ignores_texts_that_are_too_different():
    assert search("xyzqq") == []


def test_search_explanation_lists_common_letter_pairs():
    terms = [item["term"] for item in search("rosemary")[0].matched_terms]
    assert terms and all(len(term) == 2 for term in terms)


def test_index_stats():
    stats = make_recommender().index_stats()
    assert stats["documents"] == 4
    assert stats["dimensions"] == 13
    assert stats["letter_pairs"] > 0
