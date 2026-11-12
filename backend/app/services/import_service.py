"""Import du jeu de données (fichiers CSV) dans la base.

Source : Wind River Greens, « plant-variety-database », licence CC BY 4.0.
Voir backend/data/README.md.
"""
import csv
import os
import urllib.request

from sqlalchemy import delete

from ..extensions import db
from ..models import Category, Plant

DATASET_BASE_URL = (
    "https://huggingface.co/datasets/WindRiverGreens/plant-variety-database/resolve/main/"
)
DATASET_FILES = ("categories.csv", "varieties.csv")

# Colonnes de varieties.csv recopiées telles quelles dans la table plants.
TEXT_COLUMNS = (
    "name", "slug", "scientific_name", "description", "days_to_harvest",
    "days_to_germination", "plant_height", "plant_spacing", "sun_requirement",
    "water_requirement", "soil_type", "soil_ph", "growing_difficulty",
    "growing_season", "sowing_method", "color", "size", "shape",
    "flavor_profile", "culinary_uses", "disease_resistance", "common_pests",
    "common_diseases", "source_database", "url",
)
BOOLEAN_COLUMNS = ("is_container_friendly", "is_heirloom", "is_hybrid")
INTEGER_COLUMNS = ("usda_zone_min", "usda_zone_max")


def download_dataset(data_dir):
    """Télécharge les fichiers CSV manquants dans data_dir."""
    os.makedirs(data_dir, exist_ok=True)
    for filename in DATASET_FILES:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            print(f"Téléchargement de {filename}...")
            urllib.request.urlretrieve(DATASET_BASE_URL + filename, path)


def _text(value):
    value = (value or "").strip()
    return value or None


def _boolean(value):
    return (value or "").strip().lower() in ("true", "1", "yes")


def _integer(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _read_csv(path):
    # utf-8-sig : accepte un éventuel marqueur BOM en début de fichier.
    with open(path, newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def import_dataset(data_dir, reset=False):
    """Importe categories.csv puis varieties.csv. Renvoie (nb catégories, nb plantes)."""
    if reset:
        db.session.execute(delete(Plant))
        db.session.execute(delete(Category))
        db.session.commit()

    # 1. Catégories
    categories = {category.slug: category for category in db.session.scalars(db.select(Category))}
    for row in _read_csv(os.path.join(data_dir, "categories.csv")):
        slug = _text(row.get("slug"))
        if not slug or slug in categories:
            continue
        categories[slug] = Category(
            slug=slug,
            name=_text(row.get("name")) or slug,
            plural_name=_text(row.get("plural_name")),
            description=_text(row.get("description")),
        )
        db.session.add(categories[slug])
    db.session.flush()  # attribue les identifiants des catégories

    # 2. Plantes
    plant_count = 0
    for row in _read_csv(os.path.join(data_dir, "varieties.csv")):
        name = _text(row.get("name"))
        slug = _text(row.get("category"))
        if not name or not slug:
            continue  # ligne incomplète : on l'ignore
        if slug not in categories:
            # Catégorie absente de categories.csv : on la crée à la volée.
            categories[slug] = Category(slug=slug, name=slug.replace("-", " ").title())
            db.session.add(categories[slug])
            db.session.flush()

        values = {column: _text(row.get(column)) for column in TEXT_COLUMNS}
        values.update({column: _boolean(row.get(column)) for column in BOOLEAN_COLUMNS})
        values.update({column: _integer(row.get(column)) for column in INTEGER_COLUMNS})
        db.session.add(Plant(category_id=categories[slug].id, **values))
        plant_count += 1

    db.session.commit()
    return len(categories), plant_count
