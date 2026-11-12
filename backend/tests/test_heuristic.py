"""Tests de la méthode heuristique seule (sans Flask ni base de données)."""
from app.services.query_builder import build_query_parts, clean_criteria
from app.services.recommenders import HeuristicRecommender, PlantDocument


def document(plant_id, name, category, scientific_name="", **attributes):
    names = {"name": name, "scientific_name": scientific_name, "categories": list(category[1:])}
    return PlantDocument(plant_id, names, {"category": category[0], **attributes})


TOMATO = ("tomato", "tomates", "tomato")
LETTUCE = ("lettuce", "laitues et salades", "lettuce")
HERB = ("herb", "herbes aromatiques", "herb")
ROOT = ("root-vegetable", "legumes racines", "root vegetable")

DOCUMENTS = [
    document(1, "cherry tomato sweet bite", TOMATO, "solanum lycopersicum",
             sun=["full_sun"], water=["high"], difficulty=["easy"], season=["warm"], soil=["rich", "well_drained"], container=True),
    document(2, "butterhead lettuce", LETTUCE, "lactuca sativa",
             sun=["full_sun", "partial_shade"], water=["high"], difficulty=["easy"], season=["cool"], soil=["rich"], container=True),
    document(3, "rosemary", HERB, "salvia rosmarinus",
             sun=["full_sun"], water=["low"], difficulty=["easy"], season=["perennial"], soil=["sandy", "well_drained"], container=True),
    document(4, "carrot", ROOT, "daucus carota",
             sun=["full_sun"], water=["medium"], difficulty=["moderate"], season=["cool"], soil=["loam", "sandy"], container=False),
]


def make_recommender():
    recommender = HeuristicRecommender()
    recommender.fit(DOCUMENTS)
    return recommender


def recommend(criteria, **options):
    parts = build_query_parts(clean_criteria(criteria))
    return make_recommender().recommend(parts, **options)


def search(query, **options):
    return make_recommender().search(query, **options)


# ----- O2 : plantes pour un environnement -----

def test_plant_meeting_all_criteria_exactly_has_score_one():
    results = recommend({"sun": 100, "water": 10, "container": True})
    assert [(r.plant_id, r.score) for r in results] == [(3, 1.0)]


def test_one_unmet_criterion_eliminates_the_plant():
    # la tomate aime le plein soleil mais demande beaucoup d'eau : éliminée
    assert 1 not in [r.plant_id for r in recommend({"sun": 100, "water": 10})]


def test_too_strict_a_request_gives_no_result():
    assert recommend({"sun": 0, "water": 0}) == []


def test_compatible_value_scores_less_than_exact_value():
    # la laitue accepte « plein soleil » parmi d'autres : 0,75 au lieu de 1
    scores = {r.plant_id: r.score for r in recommend({"sun": 100})}
    assert scores[1] == 1.0
    assert scores[2] == 0.75


def test_ties_are_broken_by_ease_then_id():
    # 1, 3 et 4 ont le même score ; 4 est de difficulté moyenne, donc après
    assert [r.plant_id for r in recommend({"sun": 100})] == [1, 3, 4, 2]


def test_allowed_ids_and_top_k():
    assert [r.plant_id for r in recommend({"sun": 100}, allowed_ids={3, 4})] == [3, 4]
    assert len(recommend({"sun": 100}, top_k=2)) == 2


def test_no_criteria_gives_no_result():
    assert make_recommender().recommend([]) == []


def test_explanation_lists_the_points_of_each_criterion():
    result = recommend({"sun": 100, "water": 100})[0]  # la tomate : deux critères exacts
    assert result.plant_id == 1
    assert result.matched_terms == [
        {"term": "Lumière : plein soleil (100 %)", "weight": 0.5},
        {"term": "Eau : beaucoup d'eau (100 %)", "weight": 0.5},
    ]


# ----- O1 : retrouver une plante par son nom -----

def test_search_rules_from_strictest_to_loosest():
    assert [(r.plant_id, r.score) for r in search("rosemary")] == [(3, 1.0)]  # nom exact
    assert [(r.plant_id, r.score) for r in search("butter")] == [(2, 0.9)]  # début du nom
    assert [(r.plant_id, r.score) for r in search("sweet")] == [(1, 0.8)]  # début d'un mot
    assert [(r.plant_id, r.score) for r in search("arro")] == [(4, 0.7)]  # dans le nom
    assert [(r.plant_id, r.score) for r in search("laitue")] == [(2, 0.6)]  # type de plante
    assert [(r.plant_id, r.score) for r in search("daucus")] == [(4, 0.5)]  # nom latin


def test_search_gives_the_reason():
    result = search("laitue")[0]
    assert result.matched_terms == [{"term": "Le type de plante correspond à la recherche", "weight": 0.6}]


def test_search_does_not_tolerate_typos():
    assert search("rosemarry") == []


def test_search_needs_two_letters():
    assert search("r") == []


def test_index_stats():
    stats = make_recommender().index_stats()
    assert stats["documents"] == 4
    assert stats["fit_duration_ms"] >= 0
