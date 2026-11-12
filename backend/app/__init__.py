"""Fabrique de l'application Flask (pattern « application factory »).

Le backend ne renvoie que du JSON : il ne connaît pas le frontend.
C'est ce qui rend l'application « découplée ».
"""
import os

from flask import Flask, request

from .config import Config
from .extensions import db

__version__ = "0.2.0"


def create_app(config_overrides=None):
    """Crée et configure l'application.

    config_overrides : dictionnaire optionnel utilisé par les tests pour
    remplacer la configuration (par exemple l'adresse de la base de données).
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    # Le dossier « instance » contient la base SQLite en développement.
    os.makedirs(app.instance_path, exist_ok=True)

    # Les accents sont envoyés tels quels dans le JSON (pas en \uXXXX).
    app.json.ensure_ascii = False
    # Les clés gardent l'ordre du code (sinon Flask les trie par ordre alphabétique).
    app.json.sort_keys = False

    db.init_app(app)

    from .controllers import register_blueprints
    from .errors import register_error_handlers
    from .cli import register_cli

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)
    _register_cors(app)

    with app.app_context():
        from . import models  # noqa: F401  (déclare les tables auprès de l'ORM)

        db.create_all()

    return app


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
