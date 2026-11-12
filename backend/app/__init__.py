"""Fabrique de l'application Flask.

Le backend ne renvoie que du JSON : il ne connaît pas le frontend.
C'est ce qui rend l'application « découplée ».
"""
import os

from flask import Flask, request

from app.config import Config, INSTANCE_DIR

__version__ = "0.4.0"


def create_app(config_overrides=None):
    """Crée et configure l'application.

    config_overrides : dictionnaire optionnel utilisé par les tests pour
    remplacer la configuration (par exemple l'adresse de la base de données).
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # JSON : accents envoyés tels quels, clés dans l'ordre du code.
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    # Crée les tables si elles n'existent pas encore (elles sont remplies par prepa_db.py).
    from app.models import Base, get_engine
    engine = get_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    Base.metadata.create_all(engine)
    _check_database_is_up_to_date(engine)

    from app.blueprints import (
        health_bp,
        plants_bp,
        recommendations_bp,
        metrics_bp
    )

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(plants_bp, url_prefix='/api')
    app.register_blueprint(recommendations_bp, url_prefix='/api')
    app.register_blueprint(metrics_bp, url_prefix='/api')

    from app.errors import register_error_handlers
    register_error_handlers(app)
    _register_cors(app)

    return app


def _check_database_is_up_to_date(engine):
    """Arrête le démarrage avec un message clair si la base date d'une
    ancienne version du code (colonnes manquantes)."""
    from sqlalchemy import inspect

    from app.models import Plant, RecommendationRun

    inspector = inspect(engine)
    missing = set()
    for model in (Plant, RecommendationRun):
        existing = {column['name'] for column in inspector.get_columns(model.__tablename__)}
        missing |= {column.name for column in model.__table__.columns} - existing
    if missing:
        raise RuntimeError(
            "La base de données date d'une ancienne version (colonnes manquantes : "
            + ", ".join(sorted(missing))
            + "). Recrée-la avec : python prepa_db.py"
        )


def _register_cors(app):
    """Autorise le frontend (servi sur une autre adresse) à appeler l'API.

    Un navigateur bloque par défaut les requêtes vers une autre origine
    (autre port = autre origine). L'API doit donc dire explicitement quelles
    origines elle accepte : c'est le mécanisme CORS.
    """

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed = app.config["CORS_ORIGINS"]
        if origin and ("*" in allowed or origin in allowed):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
