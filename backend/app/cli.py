"""Commandes en ligne : flask --app run seed, flask --app run build-index"""
import os

import click

from .services import import_service, plant_service, recommendation_service

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")


def register_cli(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Vide les tables avant d'importer.")
    @click.option(
        "--sample",
        is_flag=True,
        help="Importe le petit échantillon de démonstration (sans téléchargement).",
    )
    def seed(reset, sample):
        """Importe le jeu de données dans la base."""
        existing = plant_service.count_plants()
        if existing and not reset:
            click.echo(f"La base contient déjà {existing} plantes. Ajoute --reset pour réimporter.")
            return

        if sample:
            data_dir = SAMPLE_DIR
        else:
            data_dir = DATA_DIR
            import_service.download_dataset(data_dir)

        category_count, plant_count = import_service.import_dataset(data_dir, reset=reset)
        recommendation_service.reset_index_cache()
        click.echo(f"Import terminé : {category_count} catégories, {plant_count} plantes.")

    @app.cli.command("build-index")
    def build_index():
        """Construit l'index de chaque approche disponible.

        Utile pour l'approche embeddings : le modèle est téléchargé et les
        vecteurs des fiches sont calculés puis gardés sur le disque. Le
        serveur démarre ensuite sans refaire ce calcul.
        """
        for key, stats in recommendation_service.build_indexes():
            click.echo(f"{key} : {stats}")
