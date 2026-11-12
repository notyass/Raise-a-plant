"""Tests de l'API de bout en bout, sur l'échantillon de 19 fiches."""


def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["plant_count"] == 19


def test_categories_have_counts(client):
    items = client.get("/api/categories").get_json()["items"]
    by_slug = {item["slug"]: item for item in items}
    assert by_slug["herb"]["plant_count"] == 3
    assert by_slug["tomato"]["plant_count"] == 2


def test_plants_pagination(client):
    data = client.get("/api/plants?per_page=5&page=2").get_json()
    assert data["total"] == 19
    assert data["pages"] == 4
    assert len(data["items"]) == 5
    assert data["items"][0]["category"]["slug"]


def test_plants_filter_and_search(client):
    data = client.get("/api/plants?category=herb").get_json()
    assert data["total"] == 3
    data = client.get("/api/plants?q=basil").get_json()
    assert [item["name"] for item in data["items"]] == ["Sweet Basil 'Large Leaf'"]


def test_plant_detail_and_404(client):
    plant_id = client.get("/api/plants?q=aloe").get_json()["items"][0]["id"]
    assert client.get(f"/api/plants/{plant_id}").get_json()["name"] == "Aloe Vera"
    response = client.get("/api/plants/99999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_invalid_page_is_rejected(client):
    assert client.get("/api/plants?page=abc").status_code == 400
    assert client.get("/api/plants?page=0").status_code == 400


def test_options_and_approaches(client):
    options = client.get("/api/options").get_json()
    assert set(options) == {"sun", "water", "soil", "season", "difficulty"}
    approaches = client.get("/api/approaches").get_json()["items"]
    assert [(a["key"], a["available"]) for a in approaches] == [("tfidf", True), ("embeddings", True)]
    assert all(a["explanation"] and a["complexity"] for a in approaches)


def test_recommendation(client):
    response = client.post(
        "/api/recommendations",
        json={"criteria": {"water": "low", "season": "perennial"}, "top_k": 3},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["approach"]["key"] == "tfidf"
    assert data["corpus_size"] == 19
    assert 1 <= data["count"] <= 3
    names = [result["plant"]["name"] for result in data["results"]]
    assert "Rosemary 'Upright Blue'" in names
    scores = [result["score"] for result in data["results"]]
    assert scores == sorted(scores, reverse=True)
    assert data["results"][0]["matched_terms"]
    assert data["timing"]["algo_ms"] >= 0
    assert data["timing"]["total_ms"] >= data["timing"]["algo_ms"]


def test_recommendation_with_category_filter(client):
    data = client.post(
        "/api/recommendations",
        json={"criteria": {"category": "lettuce", "sun": "full_sun"}},
    ).get_json()
    assert data["count"] == 2
    assert {result["plant"]["category"]["slug"] for result in data["results"]} == {"lettuce"}


def test_recommendation_errors(client):
    assert client.post("/api/recommendations", json={"criteria": {}}).status_code == 400
    assert client.post("/api/recommendations", json={"criteria": {"sun": "lune"}}).status_code == 400
    assert client.post("/api/recommendations", json={"criteria": {"category": "inconnue"}}).status_code == 400
    assert client.post("/api/recommendations", json={"criteria": {"sun": "shade"}, "top_k": 0}).status_code == 400
    assert (
        client.post(
            "/api/recommendations", json={"criteria": {"sun": "shade"}, "approach": "inconnue"}
        ).status_code
        == 400
    )
    assert client.post("/api/recommendations", data="pas du json").status_code == 400


def test_metrics_after_recommendations(client):
    for _ in range(3):
        client.post("/api/recommendations", json={"criteria": {"difficulty": "easy"}})
    data = client.get("/api/metrics").get_json()
    tfidf = next(a for a in data["approaches"] if a["key"] == "tfidf")
    assert tfidf["algo_ms"]["count"] == 3
    assert tfidf["algo_ms"]["min"] <= tfidf["algo_ms"]["mean"] <= tfidf["algo_ms"]["max"]
    assert len(tfidf["history"]) == 3
    assert tfidf["index"]["documents"] == 19
    embeddings = next(a for a in data["approaches"] if a["key"] == "embeddings")
    assert embeddings["algo_ms"]["count"] == 0
    assert embeddings["index"] is None  # jamais utilisée : index pas encore construit


def test_recommendation_with_embeddings(client):
    response = client.post(
        "/api/recommendations",
        json={
            "criteria": {"water": "low", "season": "perennial", "category": "herb"},
            "approach": "embeddings",
            "top_k": 5,
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["approach"]["key"] == "embeddings"
    assert data["count"] == 3  # la catégorie « herb » ne contient que 3 fiches
    assert {result["plant"]["category"]["slug"] for result in data["results"]} == {"herb"}
    scores = [result["score"] for result in data["results"]]
    assert scores == sorted(scores, reverse=True)
    # L'explication reprend les libellés français des critères.
    labels = {item["term"] for item in data["results"][0]["matched_terms"]}
    assert labels == {"Herb", "Peu d'eau", "Vivace (repousse chaque année)"}


def test_both_approaches_receive_the_same_query(client):
    body = {"criteria": {"sun": "full_sun", "difficulty": "easy"}}
    tfidf = client.post("/api/recommendations", json={**body, "approach": "tfidf"}).get_json()
    embeddings = client.post("/api/recommendations", json={**body, "approach": "embeddings"}).get_json()
    assert tfidf["query_text"] == embeddings["query_text"] == "full sun, easy"

    data = client.get("/api/metrics").get_json()
    counts = {a["key"]: a["algo_ms"]["count"] for a in data["approaches"]}
    assert counts == {"tfidf": 1, "embeddings": 1}
    embeddings_index = next(a for a in data["approaches"] if a["key"] == "embeddings")["index"]
    assert embeddings_index["documents"] == 19
    assert embeddings_index["dimensions"] == 256


def test_embeddings_unavailable_without_library(app, client, monkeypatch):
    from app.services.recommenders import EmbeddingRecommender

    app.config["EMBEDDING_ENCODER"] = None
    monkeypatch.setattr(
        EmbeddingRecommender, "unavailable_reason", classmethod(lambda cls: "bibliothèque absente")
    )
    approaches = client.get("/api/approaches").get_json()["items"]
    embeddings = next(a for a in approaches if a["key"] == "embeddings")
    assert embeddings["available"] is False
    assert embeddings["unavailable_reason"] == "bibliothèque absente"
    response = client.post(
        "/api/recommendations", json={"criteria": {"sun": "shade"}, "approach": "embeddings"}
    )
    assert response.status_code == 503


def test_cors_header_for_allowed_origin(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:8080"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    response = client.get("/api/health", headers={"Origin": "http://exemple-inconnu.test"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/nexiste-pas")
    assert response.status_code == 404
    assert "error" in response.get_json()
