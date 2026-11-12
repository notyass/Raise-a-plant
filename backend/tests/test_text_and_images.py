"""Tests des petits outils : simplification de texte et titre de page d'une espèce."""
import pytest

from app.services.images import lookup_title
from app.services.text_utils import simplify


def test_simplify_removes_case_accents_and_punctuation():
    assert simplify("  Maïs 'Golden'  ") == "mais golden"
    assert simplify("Légumes-racines") == "legumes racines"
    assert simplify(None) == ""


@pytest.mark.parametrize("scientific_name, expected", [
    ("Solanum lycopersicum", "Solanum lycopersicum"),
    ("Solanum lycopersicum 'Tiny Tim'", "Solanum lycopersicum"),
    ("Brassica oleracea var. botrytis", "Brassica oleracea"),
    ("Fragaria × ananassa", "Fragaria ananassa"),
    ("Echinacea x hybrida", "Echinacea hybrida"),
    ("Rosa 'Eden'", "Rosa"),
    ("", None),
    (None, None),
])
def test_lookup_title(scientific_name, expected):
    assert lookup_title(scientific_name) == expected
