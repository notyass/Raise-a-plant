"""Route de vérification : l'API répond-elle, la base est-elle remplie ?"""
from flask import Blueprint, jsonify

from ..services import plant_service

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    from .. import __version__

    return jsonify(
        {"status": "ok", "version": __version__, "plant_count": plant_service.count_plants()}
    )
