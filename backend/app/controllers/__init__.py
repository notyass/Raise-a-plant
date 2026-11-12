"""Contrôleurs (le « C » de MVC) : un Blueprint par groupe de routes.

Un contrôleur lit la requête HTTP, appelle un service et renvoie du JSON.
Il ne contient pas de logique métier.
"""
from .health_controller import health_bp
from .metrics_controller import metrics_bp
from .plants_controller import plants_bp
from .recommendations_controller import recommendations_bp


def register_blueprints(app):
    for blueprint in (health_bp, plants_bp, recommendations_bp, metrics_bp):
        app.register_blueprint(blueprint, url_prefix="/api")
