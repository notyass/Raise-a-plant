"""Prépare une plante pour les méthodes de recommandation.

Les méthodes ne lisent pas la base : elles reçoivent, pour chaque plante,
  - ses noms (pour la recherche d'une plante, objectif O1) ;
  - ses caractéristiques normalisées (pour la recherche par environnement, O2).
"""
from app.services.normalizer import text_to_codes
from app.services.text_utils import simplify


def build_names(plant):
    """Textes dans lesquels on cherche une plante, simplifiés (minuscules, sans accents).

    Exemple : {"name": "celebrity", "scientific_name": "solanum lycopersicum",
               "categories": ["tomates", "tomato"]}
    """
    category = getattr(plant, "category", None)
    categories = []
    if category is not None:
        categories = [simplify(category.name), simplify(getattr(category, "name_en", None))]
    return {
        "name": simplify(plant.name),
        "scientific_name": simplify(getattr(plant, "scientific_name", None)),
        "categories": [text for text in categories if text],
    }


def build_attributes(plant):
    """Caractéristiques normalisées d'une plante.

    Exemple : {"category": "herb", "sun": ["partial_shade", "full_sun"],
               "water": ["low"], "soil": ["sandy", "well_drained"],
               "season": ["perennial"], "difficulty": ["easy"], "container": True}
    """
    category = getattr(plant, "category", None)
    return {
        "category": category.slug if category is not None else None,
        "sun": text_to_codes(getattr(plant, "sun_codes", None)),
        "water": text_to_codes(getattr(plant, "water_codes", None)),
        "soil": text_to_codes(getattr(plant, "soil_codes", None)),
        "season": text_to_codes(getattr(plant, "season_codes", None)),
        "difficulty": text_to_codes(getattr(plant, "difficulty_codes", None)),
        "container": bool(getattr(plant, "is_container_friendly", False)),
    }
