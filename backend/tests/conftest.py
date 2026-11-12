"""Préparation commune des tests : une application avec une base SQLite temporaire."""
import os

import pytest

from app import create_app
from app.extensions import db
from app.services import import_service, recommendation_service

from .fake_encoder import fake_encoder

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample")


@pytest.fixture()
def app(tmp_path):
    database_path = str(tmp_path / "test.db").replace("\\", "/")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            # Pas de vrai modèle de langage pendant les tests.
            "EMBEDDING_ENCODER": fake_encoder,
        }
    )
    recommendation_service.reset_index_cache()
    with app.app_context():
        import_service.import_dataset(SAMPLE_DIR)

    yield app

    with app.app_context():
        db.session.remove()
        db.engine.dispose()  # libère le fichier SQLite (nécessaire sous Windows)
    recommendation_service.reset_index_cache()


@pytest.fixture()
def client(app):
    return app.test_client()
