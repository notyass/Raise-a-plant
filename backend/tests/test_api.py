"""Tests de l'API de bout en bout, sur l'échantillon de 19 fiches."""


def recommend(client, criteria, **options):
    return client.post("/api/recommendations", json={"criteria": criteria, **options})


def search(client, query, **options):
    return client.post("/api/searches", json={"query": query, **options})


def names(data):
    return [result["plant"]["name"] for result in data["results"]]


# ----- état, options, plantes -----

def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["plant_count"] == 19


def test_options_and_approaches(client):
    options = client.get("/api/options").get_json()
    assert list(options) == ["sun", "water", "difficulty", "season", "soil"]
    assert options["sun"]["type"] == "slider" and options["season"]["type"] == "choice"

    data = client.get("/api/approaches").get_json()
    assert [approach["key"] for approach in data["items"]] == ["heuristic", "vector"]
    assert list(data["objectives"]) == ["care", "environment"]
    assert all(set(approach["explanations"]) == {"care", "environment"} for approach in data["items"])


def test_categories_have_french_names_and_counts(client):
    items = client.get("/api/categories").get_json()["items"]
    by_slug = {item["slug"]: item for item in items}
    assert by_slug["herb"]["plant_count"] == 3
    assert by_slug["herb"]["name"] == "Herbes aromatiques"


def test_plants_list_with_pagination_and_filters(client):
    data = client.get("/api/plants?per_page=5&page=2").get_json()
    assert data["total"] == 19 and data["pages"] == 4 and len(data["items"]) == 5
    assert client.get("/api/plants?category=herb").get_json()["total"] == 3
    assert client.get("/api/plants?page=abc").status_code == 400


def test_plant_page_has_french_labels_and_care_advice(client):
    plant_id = search(client, "rosemary").get_json()["results"][0]["plant"]["id"]
    plant = client.get(f"/api/plants/{plant_id}").get_json()
    assert plant["name"] == "Rosemary 'Upright Blue'"
    assert plant["category"] == {"slug": "herb", "name": "Herbes aromatiques"}
    assert plant["labels"] == {
        "sun": "Plein soleil",
        "water": "Peu d'eau",
        "difficulty": "Facile",
        "season": "Vivace",
        "soil": "Sableuse ou bien drainée",
    }
    care = {item["key"]: item for item in plant["care"]}
    assert list(care) == ["sun", "water", "soil", "season", "difficulty", "container"]
    assert care["water"]["advice"] == ["Arrose peu : laisse la terre sécher entre deux arrosages."]
    assert care["sun"]["detail"] == "Full sun (6-8 hours)"  # texte d'origine conservé
    assert plant["image_url"] is None  # pas de photo tant que prepa_images.py n'a pas tourné


def test_unknown_plant_returns_404(client):
    response = client.get("/api/plants/99999")
    assert response.status_code == 404
    assert "error" in response.get_json()


# ----- O1 : retrouver une plante par son nom -----

def test_search_with_the_heuristic_method(client):
    response = search(client, "Basil")
    assert response.status_code == 201
    data = response.get_json()
    assert data["objective"] == "care"
    assert data["approach"]["key"] == "heuristic"
    assert names(data) == ["Sweet Basil 'Large Leaf'"]
    assert data["results"][0]["matched_terms"][0]["term"] == "Un mot du nom commence par la recherche"
    assert data["timing"]["total_ms"] >= data["timing"]["algo_ms"] >= 0


def test_search_by_french_plant_type(client):
    data = search(client, "tomate").get_json()
    assert data["count"] == 2
    assert {result["plant"]["category"]["slug"] for result in data["results"]} == {"tomato"}


def test_only_the_vector_method_tolerates_a_typo(client):
    assert search(client, "rosemarry", approach="heuristic").get_json()["count"] == 0
    data = search(client, "rosemarry", approach="vector").get_json()
    assert data["approach"]["key"] == "vector"
    assert names(data)[0] == "Rosemary 'Upright Blue'"


def test_search_errors(client):
    assert search(client, "").status_code == 400
    assert search(client, None).status_code == 400
    assert search(client, "basil", approach="inconnue").status_code == 400
    assert search(client, "basil", top_k=0).status_code == 400


# ----- O2 : plantes pour un environnement -----

def test_recommend_with_the_heuristic_method(client):
    response = recommend(client, {"sun": 100, "water": 10, "season": "perennial"}, top_k=5)
    assert response.status_code == 201
    data = response.get_json()
    assert data["objective"] == "environment"
    assert data["approach"]["key"] == "heuristic"
    assert data["query_text"] == "Lumière : plein soleil (100 %) · Eau : peu d'eau (10 %) · Saison : vivace"
    assert data["corpus_size"] == 19
    # filtres stricts : une seule fiche respecte les trois critères
    assert names(data) == ["Rosemary 'Upright Blue'"]
    assert data["results"][0]["score"] == 1.0
    assert sum(item["weight"] for item in data["results"][0]["matched_terms"]) == 1.0


def test_recommend_with_the_vector_method_always_answers(client):
    criteria = {"sun": 100, "water": 10, "season": "perennial"}
    data = recommend(client, criteria, approach="vector", top_k=5).get_json()
    assert data["approach"]["key"] == "vector"
    assert data["count"] == 5  # les 5 fiches les plus proches, même imparfaites
    assert names(data)[0] == "Rosemary 'Upright Blue'"
    scores = [result["score"] for result in data["results"]]
    assert scores == sorted(scores, reverse=True)
    assert 0 < scores[-1] < scores[0] <= 1


def test_too_strict_a_request_separates_the_two_methods(client):
    criteria = {"sun": 0, "water": 0, "difficulty": "difficult"}
    assert recommend(client, criteria, approach="heuristic").get_json()["count"] == 0
    assert recommend(client, criteria, approach="vector").get_json()["count"] == 10


def test_both_methods_receive_the_same_request(client):
    criteria = {"sun": 70, "difficulty": "easy"}
    heuristic = recommend(client, criteria, approach="heuristic").get_json()
    vector = recommend(client, criteria, approach="vector").get_json()
    assert heuristic["query_text"] == vector["query_text"] == "Lumière : plein soleil (70 %) · Difficulté : facile"
    assert heuristic["criteria"] == vector["criteria"]


def test_category_filters_both_methods(client):
    for approach in ("heuristic", "vector"):
        data = recommend(client, {"category": "lettuce", "sun": 100}, approach=approach).get_json()
        assert data["count"] == 2
        assert {result["plant"]["category"]["slug"] for result in data["results"]} == {"lettuce"}


def test_recommendation_errors(client):
    assert recommend(client, {}).status_code == 400
    assert recommend(client, {"sun": 150}).status_code == 400
    assert recommend(client, {"season": "mousson"}).status_code == 400
    assert recommend(client, {"category": "inconnue"}).status_code == 400
    assert recommend(client, {"sun": 50}, top_k=0).status_code == 400
    assert recommend(client, {"sun": 50}, approach="inconnue").status_code == 400
    assert client.post("/api/recommendations", data="pas du json").status_code == 400


# ----- tableau de bord -----

def test_metrics_by_method_and_objective(client):
    for _ in range(3):
        recommend(client, {"sun": 100}, approach="heuristic")
    recommend(client, {"sun": 0, "water": 0}, approach="heuristic")  # aucun résultat
    recommend(client, {"sun": 100}, approach="vector")
    search(client, "basil", approach="vector")

    data = client.get("/api/metrics").get_json()
    by_key = {approach["key"]: approach for approach in data["approaches"]}
    assert list(by_key) == ["heuristic", "vector"]

    heuristic = by_key["heuristic"]["objectives"]
    assert heuristic["environment"]["algo_ms"]["count"] == 4
    assert heuristic["environment"]["empty_count"] == 1
    assert len(heuristic["environment"]["history"]) == 4
    assert heuristic["care"]["algo_ms"]["count"] == 0
    assert by_key["heuristic"]["index"]["documents"] == 19

    vector = by_key["vector"]["objectives"]
    assert vector["environment"]["algo_ms"]["count"] == 1
    assert vector["care"]["algo_ms"]["count"] == 1
    assert by_key["vector"]["index"]["dimensions"] == 13


def test_metrics_before_any_search(client):
    data = client.get("/api/metrics").get_json()
    for approach in data["approaches"]:
        assert approach["index"] is None
        assert all(measures["algo_ms"]["count"] == 0 for measures in approach["objectives"].values())


# ----- divers -----

def test_cors_header_for_allowed_origin(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:8080"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    response = client.get("/api/health", headers={"Origin": "http://exemple-inconnu.test"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/nexiste-pas")
    assert response.status_code == 404
    assert "error" in response.get_json()
