from flask import Blueprint, jsonify

from app.services.PlantService import PlantService

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """l'API répond-elle, la base est-elle remplie ?"""
    from app import __version__

    ps = PlantService()
    return jsonify({'status': 'ok', 'version': __version__, 'plant_count': ps.countPlants()})
