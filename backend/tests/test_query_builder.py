"""Tests de la construction du texte de requête."""
import pytest

from app.errors import ApiError
from app.services.query_builder import build_query_parts, build_query_text, clean_criteria


def test_empty_values_are_removed():
    assert clean_criteria({"sun": "", "water": None, "container": False}) == {}


def test_valid_criteria_are_kept():
    criteria = {"sun": "full_sun", "difficulty": "easy", "container": True, "keywords": "  salad "}
    assert clean_criteria(criteria) == {
        "sun": "full_sun",
        "difficulty": "easy",
        "container": True,
        "keywords": "salad",
    }


def test_unknown_key_is_rejected():
    with pytest.raises(ApiError):
        clean_criteria({"couleur": "rouge"})


def test_unknown_value_is_rejected():
    with pytest.raises(ApiError):
        clean_criteria({"sun": "lune"})


def test_criteria_must_be_an_object():
    with pytest.raises(ApiError):
        clean_criteria(["full_sun"])


def test_query_text_uses_english_terms():
    cleaned = clean_criteria({"sun": "full_sun", "water": "low", "container": True, "keywords": "pesto"})
    text = build_query_text(cleaned, category_name="Herb")
    assert text == "Herb, full sun, low water drought tolerant, container friendly, pesto"


def test_query_parts_have_french_labels():
    cleaned = clean_criteria({"sun": "full_sun", "container": True})
    assert build_query_parts(cleaned) == [
        {"label": "Plein soleil", "text": "full sun"},
        {"label": "Culture en pot", "text": "container friendly"},
    ]


def test_no_criteria_gives_empty_text():
    assert build_query_text({}) == ""
