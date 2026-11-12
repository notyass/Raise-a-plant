"""Prépare la base de données : crée les tables, importe le jeu de données
et normalise les caractéristiques des plantes (soleil, eau, terre, saison,
difficulté) pour les deux méthodes et l'affichage en français. Si le fichier
data/images.json existe (voir prepa_images.py), les photos sont ajoutées.

    python prepa_db.py              réinitialise la base avec les 1 972 plantes
    python prepa_db.py --sample     utilise les 19 fiches d'exemple (sans téléchargement)
    python prepa_db.py --if-empty   ne fait rien si la base contient déjà des plantes

Source des données : Wind River Greens, « plant-variety-database »,
licence CC BY 4.0 (voir data/README.md).
"""
import argparse
import csv
import json
import os
import urllib.request

from app.services.images import lookup_title
from app.services.normalizer import SOURCE_COLUMNS, category_name_fr, codes_to_text, normalize

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
SAMPLE_DIR = os.path.join(DATA_DIR, 'sample')
IMAGES_FILE = os.path.join(DATA_DIR, 'images.json')
IMAGE_COLUMNS = ('image_url', 'image_author', 'image_license', 'image_page_url')

DATASET_BASE_URL = (
    "https://huggingface.co/datasets/WindRiverGreens/plant-variety-database/resolve/main/"
)
DATASET_FILES = ('categories.csv', 'varieties.csv')

# Colonnes de varieties.csv recopiées telles quelles dans la table plants.
TEXT_COLUMNS = (
    'name', 'slug', 'scientific_name', 'description', 'days_to_harvest',
    'days_to_germination', 'plant_height', 'plant_spacing', 'sun_requirement',
    'water_requirement', 'soil_type', 'soil_ph', 'growing_difficulty',
    'growing_season', 'sowing_method', 'color', 'size', 'shape',
    'flavor_profile', 'culinary_uses', 'disease_resistance', 'common_pests',
    'common_diseases', 'source_database', 'url',
)
BOOLEAN_COLUMNS = ('is_container_friendly', 'is_heirloom', 'is_hybrid')
INTEGER_COLUMNS = ('usda_zone_min', 'usda_zone_max')


def download_dataset(data_dir):
    """Télécharge les fichiers CSV manquants dans data_dir."""
    os.makedirs(data_dir, exist_ok=True)
    for filename in DATASET_FILES:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            print(f"[*] Téléchargement de {filename}...")
            urllib.request.urlretrieve(DATASET_BASE_URL + filename, path)


def _text(value):
    value = (value or '').strip()
    return value or None


def _boolean(value):
    return (value or '').strip().lower() in ('true', '1', 'yes')


def _integer(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _read_csv(path):
    # utf-8-sig : accepte un éventuel marqueur BOM en début de fichier
    with open(path, newline='', encoding='utf-8-sig') as csv_file:
        return list(csv.DictReader(csv_file))


def build_category_values(row):
    """Valeurs d'une catégorie à partir d'une ligne de categories.csv."""
    slug = _text(row.get('slug'))
    name_en = _text(row.get('name')) or slug
    return {
        'slug': slug,
        'name': category_name_fr(slug, default=name_en),  # nom français affiché
        'name_en': name_en,
        'plural_name': _text(row.get('plural_name')),
        'description': _text(row.get('description')),
    }


def load_images(images_file=IMAGES_FILE):
    """Photos trouvées par prepa_images.py : {titre cherché: {image_url, image_author, ...}}."""
    if not os.path.exists(images_file):
        return {}
    with open(images_file, encoding='utf-8') as json_file:
        return json.load(json_file)


def build_plant_values(row, images=None):
    """Valeurs d'une plante à partir d'une ligne de varieties.csv.

    images : dictionnaire renvoyé par load_images(), ou None."""
    values = {}
    for column in TEXT_COLUMNS:
        values[column] = _text(row.get(column))
    for column in BOOLEAN_COLUMNS:
        values[column] = _boolean(row.get(column))
    for column in INTEGER_COLUMNS:
        values[column] = _integer(row.get(column))
    # normalisation : texte libre anglais -> codes (ex. "full_sun,partial_shade")
    for key, source_column in SOURCE_COLUMNS.items():
        values[f'{key}_codes'] = codes_to_text(normalize(key, values[source_column]))
    # photo de l'espèce, si prepa_images.py en a trouvé une
    image = (images or {}).get(lookup_title(values['scientific_name'])) or {}
    for column in IMAGE_COLUMNS:
        values[column] = image.get(column)
    return values


def setup_database(db_uri=None, data_dir=None, if_empty=False):
    """Réinitialise la base db_uri et importe les CSV de data_dir via l'ORM.

    Retourne (nombre de catégories, nombre de plantes).
    """
    from sqlalchemy.orm import sessionmaker

    from app.config import Config, INSTANCE_DIR
    from app.models import Base, Category, Plant, get_engine

    if db_uri is None:
        db_uri = Config.SQLALCHEMY_DATABASE_URI
        os.makedirs(INSTANCE_DIR, exist_ok=True)
    if data_dir is None:
        data_dir = DATA_DIR

    engine = get_engine(db_uri)
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    if if_empty:
        Base.metadata.create_all(engine)
        session = SessionFactory()
        try:
            existing = session.query(Plant).count()
        finally:
            session.close()
        if existing:
            print(f"[=] La base contient déjà {existing} plantes : rien à faire.")
            return None

    print(f"[*] Initialisation de la base de données via SQLAlchemy ORM : {db_uri}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    images = load_images()
    session = SessionFactory()
    try:
        # 1. catégories
        categories_map = {}
        for row in _read_csv(os.path.join(data_dir, 'categories.csv')):
            slug = _text(row.get('slug'))
            if not slug or slug in categories_map:
                continue
            c = Category(**build_category_values(row))
            categories_map[slug] = c
            session.add(c)

        # 2. plantes
        plant_count = 0
        for row in _read_csv(os.path.join(data_dir, 'varieties.csv')):
            name = _text(row.get('name'))
            slug = _text(row.get('category'))
            if not name or not slug:
                continue  # ligne incomplète : on l'ignore
            if slug not in categories_map:
                # catégorie absente de categories.csv : on la crée à la volée
                c = Category(**build_category_values({'slug': slug, 'name': slug.replace('-', ' ').title()}))
                categories_map[slug] = c
                session.add(c)

            plant = Plant(**build_plant_values(row, images))
            plant.category = categories_map[slug]  # l'ORM remplit category_id tout seul
            session.add(plant)
            plant_count += 1

        session.commit()
        print(f"[+] Base initialisée : {len(categories_map)} catégories, {plant_count} plantes.")
        if not images:
            print("[i] Pas de photos : lance python prepa_images.py pour en ajouter.")
        return len(categories_map), plant_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Prépare la base de données de l'application.")
    parser.add_argument('--sample', action='store_true',
                        help="importe les 19 fiches d'exemple, sans téléchargement")
    parser.add_argument('--if-empty', action='store_true',
                        help="ne fait rien si la base contient déjà des plantes")
    args = parser.parse_args()

    if args.sample:
        setup_database(data_dir=SAMPLE_DIR, if_empty=args.if_empty)
    else:
        download_dataset(DATA_DIR)
        setup_database(data_dir=DATA_DIR, if_empty=args.if_empty)
