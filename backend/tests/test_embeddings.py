"""Tests de l'approche embeddings seule, avec un faux encodeur (sans modèle)."""
import numpy as np

from app.services.recommenders import EmbeddingRecommender, PlantDocument

from .fake_encoder import fake_encoder

DOCUMENTS = [
    PlantDocument(1, "Cherry tomato. Full sun. High consistent moisture. Easy. Warm season."),
    PlantDocument(2, "Butterhead lettuce. Partial shade. Cool season. Very easy."),
    PlantDocument(3, "Rosemary herb. Full sun. Low water, drought tolerant. Perennial."),
    PlantDocument(4, "Carrot root vegetable. Full sun. Cool season. Moderate."),
]


def make_recommender(**options):
    recommender = EmbeddingRecommender(encoder=fake_encoder, **options)
    recommender.fit(DOCUMENTS)
    return recommender


def test_vectors_are_normalized():
    norms = np.linalg.norm(make_recommender().matrix, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_best_match_comes_first():
    results = make_recommender().recommend("drought tolerant perennial", top_k=3)
    assert results[0].plant_id == 3


def test_identical_text_has_score_one():
    result = make_recommender().recommend(DOCUMENTS[1].text, top_k=1)[0]
    assert result.plant_id == 2
    assert abs(result.score - 1.0) < 1e-5


def test_scores_are_sorted():
    scores = [result.score for result in make_recommender().recommend("full sun easy", top_k=4)]
    assert scores == sorted(scores, reverse=True)


def test_always_returns_top_k_even_without_common_word():
    # Différence avec TF-IDF : chaque fiche a un score, même faible.
    assert len(make_recommender().recommend("zzzz", top_k=3)) == 3


def test_allowed_ids_filters_results():
    results = make_recommender().recommend("full sun", top_k=4, allowed_ids={2, 4})
    assert sorted(result.plant_id for result in results) == [2, 4]


def test_explanation_ranks_criteria_by_similarity():
    parts = [
        {"label": "Vivace", "text": "perennial"},
        {"label": "Saison fraîche", "text": "cool season"},
    ]
    result = make_recommender().recommend("perennial cool season", top_k=4, allowed_ids={3}, query_parts=parts)[0]
    assert [item["term"] for item in result.matched_terms] == ["Vivace", "Saison fraîche"]
    assert result.matched_terms[0]["weight"] > result.matched_terms[1]["weight"]


def test_no_query_parts_gives_no_explanation():
    assert make_recommender().recommend("full sun", top_k=1)[0].matched_terms == []


def test_vectors_are_cached_on_disk(tmp_path):
    calls = []

    def counting_encoder(texts):
        calls.append(len(texts))
        return fake_encoder(texts)

    first = EmbeddingRecommender(encoder=counting_encoder, cache_dir=str(tmp_path))
    first.fit(DOCUMENTS)
    assert first.loaded_from_cache is False
    assert len(list(tmp_path.glob("embeddings_*.npy"))) == 1

    calls.clear()
    second = EmbeddingRecommender(encoder=counting_encoder, cache_dir=str(tmp_path))
    second.fit(DOCUMENTS)
    assert second.loaded_from_cache is True
    assert calls == [1]  # seul l'appel d'échauffement, les 4 fiches ne sont pas réencodées
    assert np.allclose(first.matrix, second.matrix)


def test_cache_is_ignored_when_documents_change(tmp_path):
    EmbeddingRecommender(encoder=fake_encoder, cache_dir=str(tmp_path)).fit(DOCUMENTS)
    changed = EmbeddingRecommender(encoder=fake_encoder, cache_dir=str(tmp_path))
    changed.fit(DOCUMENTS[:3])
    assert changed.loaded_from_cache is False
    assert changed.matrix.shape[0] == 3


def test_index_stats():
    stats = make_recommender().index_stats()
    assert stats["documents"] == 4
    assert stats["dimensions"] == 256
    assert stats["matrix_memory_kb"] == 4.0  # 4 fiches × 256 nombres × 4 octets
