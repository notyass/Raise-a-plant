"""Tests des critères et de la construction de la demande (O2)."""
import pytest

from app.errors import ApiError
from app.services.query_builder import (
    build_query_parts, clean_criteria, codes_label, codes_position, describe_query,
    level_position, slider_choice,
)


def test_empty_values_are_removed():
    assert clean_criteria({"sun": None, "difficulty": "", "container": False}) == {}


def test_valid_criteria_are_kept():
    criteria = {"sun": 80, "water": 0, "difficulty": "easy", "container": True}
    assert clean_criteria(criteria) == criteria


def test_slider_must_be_a_number_between_0_and_100():
    for value in (150, -1, "80", True):
        with pytest.raises(ApiError):
            clean_criteria({"sun": value})


def test_unknown_key_or_value_is_rejected():
    with pytest.raises(ApiError):
        clean_criteria({"couleur": "rouge"})
    with pytest.raises(ApiError):
        clean_criteria({"season": "mousson"})
    with pytest.raises(ApiError):
        clean_criteria(["full_sun"])


def test_slider_is_cut_in_equal_parts():
    assert [slider_choice("sun", value)["value"] for value in (0, 33, 34, 66, 67, 100)] == [
        "shade", "shade", "partial_shade", "partial_shade", "full_sun", "full_sun",
    ]


def test_levels_are_placed_between_0_and_1():
    assert level_position("sun", "shade") == 0.0
    assert level_position("sun", "partial_shade") == 0.5
    assert level_position("sun", "full_sun") == 1.0
    assert codes_position("sun", ["partial_shade", "full_sun"]) == 0.75
    assert codes_position("water", []) is None


def test_query_parts_serve_both_methods():
    parts = build_query_parts(clean_criteria({"sun": 80, "difficulty": "easy", "container": True}))
    assert parts == [
        {"key": "sun", "code": "full_sun", "value": 0.8, "label": "Lumière : plein soleil (80 %)"},
        {"key": "difficulty", "code": "easy", "value": 0.0, "label": "Difficulté : facile"},
        {"key": "container", "code": True, "value": 1.0, "label": "Culture en pot"},
    ]


def test_category_comes_first_in_query_parts():
    category = {"slug": "herb", "label": "Herbes aromatiques"}
    parts = build_query_parts(clean_criteria({"water": 10}), category=category)
    assert parts[0] == {"key": "category", "code": "herb", "value": 1.0, "label": "Type : Herbes aromatiques"}


def test_describe_query():
    parts = build_query_parts(clean_criteria({"sun": 80, "season": "cool"}))
    assert describe_query(parts) == "Lumière : plein soleil (80 %) · Saison : saison fraîche"
    assert describe_query([]) == ""


def test_codes_label_in_french():
    assert codes_label("sun", ["full_sun", "partial_shade"]) == "Mi-ombre ou plein soleil"
    assert codes_label("soil", ["sandy", "rich", "well_drained"]) == "Sableuse, riche ou bien drainée"
    assert codes_label("difficulty", ["easy"]) == "Facile"
    assert codes_label("water", []) is None
