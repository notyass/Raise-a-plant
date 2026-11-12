"""Tests des conseils d'entretien générés pour la page d'une plante (O1)."""
from app.services.care_guide import build_care


class FakePlant:
    sun_requirement = "Full sun to partial shade (4-6 hours)"
    water_requirement = "Low — drought tolerant"
    soil_type = None
    growing_season = "Perennial"
    growing_difficulty = "Easy"


ATTRIBUTES = {
    "sun": ["full_sun", "partial_shade"],
    "water": ["low"],
    "soil": [],
    "season": ["perennial"],
    "difficulty": ["easy"],
    "container": True,
}


def test_one_advice_per_known_characteristic():
    care = build_care(FakePlant(), ATTRIBUTES)
    assert [item["key"] for item in care] == ["sun", "water", "season", "difficulty", "container"]


def test_advice_is_in_french_with_the_original_text():
    water = next(item for item in build_care(FakePlant(), ATTRIBUTES) if item["key"] == "water")
    assert water["title"] == "Arrosage"
    assert water["advice"] == ["Arrose peu : laisse la terre sécher entre deux arrosages."]
    assert water["detail"] == "Low — drought tolerant"


def test_several_codes_give_several_sentences():
    sun = build_care(FakePlant(), ATTRIBUTES)[0]
    assert len(sun["advice"]) == 2


def test_original_text_is_kept_when_no_code_was_recognized():
    plant = FakePlant()
    plant.soil_type = "Soilless growing medium"
    soil = next(item for item in build_care(plant, ATTRIBUTES) if item["key"] == "soil")
    assert soil["advice"] == [] and soil["detail"] == "Soilless growing medium"


def test_no_container_advice_when_not_container_friendly():
    care = build_care(FakePlant(), {**ATTRIBUTES, "container": False})
    assert "container" not in [item["key"] for item in care]
