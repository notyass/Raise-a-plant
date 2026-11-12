"""Tests de la normalisation des textes du jeu de données en codes."""
import pytest

from app.services.normalizer import (
    CATEGORY_NAMES_FR, RULES, category_name_fr, codes_to_text, normalize, text_to_codes,
)
from app.services.query_builder import CRITERIA


@pytest.mark.parametrize("text, expected", [
    ("Full sun (6+ hours)", ["full_sun"]),
    ("Full sun to partial shade (4-6+ hours)", ["full_sun", "partial_shade"]),
    ("Partial shade (4-6 hours)", ["partial_shade"]),
    ("Full shade (2-4 hours)", ["shade"]),
    ("Dappled Sunlight", ["partial_shade"]),
])
def test_sun(text, expected):
    assert normalize("sun", text) == expected


@pytest.mark.parametrize("text, expected", [
    ("High — consistent moisture needed", ["high"]),
    ("Moderate — regular watering", ["medium"]),
    ("1-1.5 inches per week, consistent moisture", ["medium"]),
    ("Moderate; drought tolerant once established", ["low", "medium"]),
    ("Low — drought tolerant", ["low"]),
    ("1-2 inches per week, deep watering", ["high"]),
    ("Keep soil consistently moist but not waterlogged", ["medium"]),
])
def test_water(text, expected):
    assert normalize("water", text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Well-drained, fertile soil with good organic content", ["rich", "well_drained"]),
    ("Well-drained sandy loam", ["loam", "sandy", "well_drained"]),
    ("Any moist soil, tolerates clay", ["clay"]),
])
def test_soil(text, expected):
    assert normalize("soil", text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Warm season annual", ["warm"]),
    ("Cool season", ["cool"]),
    ("Perennial", ["perennial"]),
    ("Year-round indoors", ["year_round"]),
    ("Spring and Summer", ["warm"]),
    ("Spring", ["warm", "cool"]),
    ("Spring through fall", ["warm", "cool"]),
    ("Biennial", []),
])
def test_season(text, expected):
    assert normalize("season", text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Easy", ["easy"]),
    ("Very Easy", ["easy"]),
    ("Easy to moderate", ["easy", "moderate"]),
    ("Moderate to Challenging", ["moderate", "difficult"]),
    ("Advanced", ["difficult"]),
])
def test_difficulty(text, expected):
    assert normalize("difficulty", text) == expected


def test_empty_text_gives_no_code():
    assert normalize("sun", None) == []
    assert normalize("water", "") == []


def test_codes_are_stored_as_text():
    assert codes_to_text(["full_sun", "partial_shade"]) == "full_sun,partial_shade"
    assert codes_to_text([]) is None
    assert text_to_codes("full_sun,partial_shade") == ["full_sun", "partial_shade"]
    assert text_to_codes(None) == []


def test_codes_are_the_same_as_the_form_choices():
    # Les codes produits par les règles doivent exister dans le formulaire.
    for key, rules in RULES.items():
        form_values = {choice["value"] for choice in CRITERIA[key]["choices"]}
        assert {code for code, _ in rules} == form_values


def test_category_names():
    assert category_name_fr("tomato") == "Tomates"
    assert category_name_fr("inconnue", default="Unknown") == "Unknown"
    assert len(CATEGORY_NAMES_FR) == 30
