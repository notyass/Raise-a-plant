from flask import Blueprint, current_app, jsonify, request

from app.errors import ApiError
from app.services.PlantService import PlantService

plants_bp = Blueprint('plants', __name__)


def _positive_int(name, default, maximum=None):
    """lit un entier positif dans l'URL (?page=2), avec valeur par défaut"""
    raw = request.args.get(name)
    if raw in (None, ''):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(f"« {name} » doit être un entier.")
    if value < 1:
        raise ApiError(f"« {name} » doit être supérieur ou égal à 1.")
    return min(value, maximum) if maximum else value


@plants_bp.route('/categories', methods=['GET'])
def categories():
    """types de plantes avec leur nombre de fiches"""
    ps = PlantService()
    return jsonify({'items': ps.getCategories()})


@plants_bp.route('/plants', methods=['GET'])
def plants():
    """liste paginée des plantes avec filtrage par query params possible (category, q)"""
    ps = PlantService()
    page = _positive_int('page', 1)
    per_page = _positive_int(
        'per_page',
        current_app.config['DEFAULT_PER_PAGE'],
        maximum=current_app.config['MAX_PER_PAGE'],
    )
    result = ps.getPlantsPage(
        category_slug=request.args.get('category') or None,
        search=(request.args.get('q') or '').strip() or None,
        page=page,
        per_page=per_page,
    )
    return jsonify(result)


@plants_bp.route('/plants/<int:plant_id>', methods=['GET'])
def plant_detail(plant_id):
    """page d'une plante : sa fiche et ses conseils d'entretien (objectif O1)"""
    ps = PlantService()
    plant = ps.getPlantById(plant_id)
    if plant is None:
        raise ApiError("Plante introuvable.", status_code=404)
    return jsonify(PlantService.describePlant(plant, with_care=True))
