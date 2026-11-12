"""Routes du catalogue : catégories et plantes."""
from flask import Blueprint, current_app, jsonify, request

from ..errors import ApiError
from ..services import plant_service

plants_bp = Blueprint("plants", __name__)


def _positive_int(name, default, maximum=None):
    """Lit un entier positif dans l'URL (?page=2), avec valeur par défaut."""
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(f"« {name} » doit être un entier.")
    if value < 1:
        raise ApiError(f"« {name} » doit être supérieur ou égal à 1.")
    return min(value, maximum) if maximum else value


@plants_bp.get("/categories")
def list_categories():
    return jsonify({"items": plant_service.list_categories()})


@plants_bp.get("/plants")
def list_plants():
    page = _positive_int("page", 1)
    per_page = _positive_int(
        "per_page",
        current_app.config["DEFAULT_PER_PAGE"],
        maximum=current_app.config["MAX_PER_PAGE"],
    )
    result = plant_service.list_plants(
        category_slug=request.args.get("category") or None,
        search=(request.args.get("q") or "").strip() or None,
        page=page,
        per_page=per_page,
    )
    return jsonify(result)


@plants_bp.get("/plants/<int:plant_id>")
def get_plant(plant_id):
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise ApiError("Plante introuvable.", status_code=404)
    return jsonify(plant.to_dict())
