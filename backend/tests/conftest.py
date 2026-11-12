"""Préparation commune des tests : une application avec une base SQLite temporaire."""
import pytest

import prepa_db
from app import create_app
from app.models import dispose_engines
from app.services.RecommendationService import reset_index_cache


@pytest.fixture()
def app(tmp_path):
    database_path = str(tmp_path / "test.db").replace("\\", "/")
    db_uri = f"sqlite:///{database_path}"

    # Base de test remplie avec les 19 fiches d'exemple.
    prepa_db.setup_database(db_uri=db_uri, data_dir=prepa_db.SAMPLE_DIR)
    reset_index_cache()

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_uri})

    yield app

    dispose_engines()  # libère le fichier SQLite (nécessaire sous Windows)
    reset_index_cache()


@pytest.fixture()
def client(app):
    return app.test_client()
