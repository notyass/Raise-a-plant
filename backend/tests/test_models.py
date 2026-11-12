"""Tests de la couche modèles : mixins et DAO, sur l'échantillon de 19 fiches."""
import json

import pytest

import prepa_db
from app.models import Plant, PlantORM, RecommendationRunORM, dispose_engines


@pytest.fixture()
def pdao(app):
    return PlantORM(app.config["SQLALCHEMY_DATABASE_URI"])


def test_count_and_find_all(pdao):
    assert pdao.count() == 19
    plants = pdao.findAll()
    assert len(plants) == 19
    assert all(isinstance(plant, Plant) for plant in plants)


def test_category_is_usable_after_session_is_closed(pdao):
    plant = pdao.findAll()[0]
    assert plant.category.slug  # préchargée par joinedload


def test_find_by_id(pdao):
    first = pdao.findAll()[0]
    assert pdao.findById(first.id).name == first.name
    assert pdao.findById(99999) is None


def test_find_by_ids(pdao):
    ids = [plant.id for plant in pdao.findAll()[:3]]
    assert sorted(plant.id for plant in pdao.findByIds(ids)) == sorted(ids)
    assert pdao.findByIds([]) == []


def test_find_page_with_filters(pdao):
    plants, total = pdao.findPage(page=2, per_page=5)
    assert total == 19 and len(plants) == 5
    plants, total = pdao.findPage(category_slug="herb")
    assert total == 3 and {plant.category.slug for plant in plants} == {"herb"}
    plants, total = pdao.findPage(search="BASIL")
    assert total == 1 and plants[0].name == "Sweet Basil 'Large Leaf'"


def test_categories(pdao):
    tomato = pdao.findCategoryBySlug("tomato")
    assert tomato.name == "Tomates" and tomato.name_en == "Tomato"
    assert pdao.findCategoryBySlug("inconnue") is None
    assert len(pdao.findIdsByCategory("lettuce")) == 2
    counts = {category.slug: count for category, count in pdao.findAllCategoriesWithCount()}
    assert counts["herb"] == 3
    assert len(counts) == 12


def test_base_model_mixin(pdao):
    plant = pdao.findAll()[0]
    data = plant.to_dict()
    assert data["name"] == plant.name
    assert data["category"] == {"slug": plant.category.slug, "name": plant.category.name}
    assert plant["name"] == plant.name  # accès façon dictionnaire
    with pytest.raises(KeyError):
        plant["colonne_inconnue"]


def test_normalized_codes_are_stored(pdao):
    rosemary = pdao.findPage(search="rosemary")[0][0]
    assert rosemary.sun_codes == "full_sun"
    assert rosemary.water_codes == "low"
    assert rosemary.season_codes == "perennial"
    assert rosemary.difficulty_codes == "easy"
    assert rosemary.soil_codes == "sandy,well_drained"


def test_timestamp_mixin(pdao):
    plant = pdao.findAll()[0]
    assert plant.created_at is not None
    assert isinstance(plant.to_dict()["created_at"], str)


def test_recommendation_run_dao(app):
    rdao = RecommendationRunORM(app.config["SQLALCHEMY_DATABASE_URI"])
    assert rdao.findAll() == []
    run = rdao.add("vector", "environment", 1.5, 2.5, 3, 19, "Lumière : plein soleil (80 %)")
    assert run.id is not None
    runs = rdao.findAll()
    assert len(runs) == 1
    assert runs[0].approach == "vector" and runs[0].objective == "environment"
    assert runs[0].created_at is not None


def test_plants_have_no_photo_without_images_file(pdao):
    assert all(plant.image_url is None for plant in pdao.findAll())


def test_photos_are_added_from_the_images_file(tmp_path):
    photo = {
        "image_url": "https://exemple.test/tomate.jpg",
        "image_author": "Une autrice",
        "image_license": "CC BY-SA 4.0",
        "image_page_url": "https://exemple.test/page-du-fichier",
    }
    images_file = tmp_path / "images.json"
    images_file.write_text(json.dumps({"Solanum lycopersicum": photo}), encoding="utf-8")
    db_uri = "sqlite:///" + str(tmp_path / "photos.db").replace("\\", "/")

    prepa_db.setup_database(db_uri=db_uri, data_dir=prepa_db.SAMPLE_DIR, images_file=str(images_file))
    try:
        plants = PlantORM(db_uri).findAll()
        tomatoes = [plant for plant in plants if plant.category.slug == "tomato"]
        others = [plant for plant in plants if plant.category.slug != "tomato"]
        # les deux tomates partagent la photo de leur espèce, avec son crédit
        assert len(tomatoes) == 2
        assert all(plant.image_url == photo["image_url"] for plant in tomatoes)
        assert all(plant.image_author == "Une autrice" for plant in tomatoes)
        assert all(plant.image_url is None for plant in others)
    finally:
        dispose_engines()  # libère le fichier SQLite (nécessaire sous Windows)
