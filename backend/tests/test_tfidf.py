"""Tests de l'approche TF-IDF seule (sans Flask ni base de données)."""
from app.services.recommenders import PlantDocument, TfidfRecommender
from app.services.recommenders.tfidf import analyze

DOCUMENTS = [
    PlantDocument(1, "Cherry tomato. Full sun. High consistent moisture. Easy. Warm season."),
    PlantDocument(2, "Butterhead lettuce. Partial shade. Cool season. Very easy."),
    PlantDocument(3, "Rosemary herb. Full sun. Low water, drought tolerant. Perennial."),
    PlantDocument(4, "Carrot root vegetable. Full sun. Cool season. Moderate."),
]


def make_recommender():
    recommender = TfidfRecommender()
    recommender.fit(DOCUMENTS)
    return recommender


def test_best_match_comes_first():
    results = make_recommender().recommend("drought tolerant perennial", top_k=3)
    assert results[0].plant_id == 3


def test_scores_are_sorted_and_between_0_and_1():
    results = make_recommender().recommend("full sun easy warm season", top_k=4)
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0 < score <= 1.0001 for score in scores)


def test_top_k_limits_the_number_of_results():
    results = make_recommender().recommend("full sun", top_k=2)
    assert len(results) == 2


def test_documents_without_common_term_are_excluded():
    results = make_recommender().recommend("partial shade", top_k=4)
    assert [result.plant_id for result in results] == [2]


def test_unknown_words_give_no_result():
    assert make_recommender().recommend("zzzz qqqq", top_k=4) == []


def test_allowed_ids_filters_results():
    results = make_recommender().recommend("full sun", top_k=4, allowed_ids={4})
    assert [result.plant_id for result in results] == [4]


def test_matched_terms_explain_the_score():
    result = make_recommender().recommend("drought tolerant", top_k=1)[0]
    terms = [item["term"] for item in result.matched_terms]
    assert "drought tolerant" in terms
    assert all(item["weight"] > 0 for item in result.matched_terms)


def test_identical_text_has_score_one():
    result = make_recommender().recommend(DOCUMENTS[1].text, top_k=1)[0]
    assert result.plant_id == 2
    assert abs(result.score - 1.0) < 1e-6


def test_index_stats():
    stats = make_recommender().index_stats()
    assert stats["documents"] == 4
    assert stats["vocabulary_size"] > 0
    assert stats["fit_duration_ms"] >= 0


def test_analyze_makes_words_and_pairs():
    assert analyze("Full sun") == ["full", "sun", "full sun"]


def test_analyze_pairs_do_not_cross_punctuation():
    terms = analyze("Full sun. Easy, well-drained soil")
    assert "sun easy" not in terms
    assert "well drained" in terms


def test_analyze_removes_stop_words():
    assert analyze("the soil and the water") == ["soil", "water", "soil water"]
