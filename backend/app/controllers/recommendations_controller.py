"""Routes de recommandation."""
from flask import Blueprint, current_app, jsonify, request

from ..errors import ApiError
from ..services import query_builder, recommendation_service

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.get("/options")
def get_options():
    """Critères du formulaire et leurs choix."""
    return jsonify(query_builder.get_options())


@recommendations_bp.get("/approaches")
def list_approaches():
    """Approches de recommandation disponibles et prévues."""
    return jsonify({"items": recommendation_service.describe_approaches()})


@recommendations_bp.post("/recommendations")
def create_recommendation():
    """Calcule une recommandation.

    Corps JSON attendu :
        {"criteria": {"sun": "full_sun", "difficulty": "easy"},
         "approach": "tfidf", "top_k": 10}
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("Le corps de la requête doit être un objet JSON.")

    top_k = payload.get("top_k", current_app.config["DEFAULT_TOP_K"])
    max_top_k = current_app.config["MAX_TOP_K"]
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= max_top_k:
        raise ApiError(f"« top_k » doit être un entier entre 1 et {max_top_k}.")

    approach = payload.get("approach", "tfidf")
    if not isinstance(approach, str):
        raise ApiError("« approach » doit être un texte.")

    result = recommendation_service.recommend(
        criteria=payload.get("criteria", {}),
        approach=approach,
        top_k=top_k,
    )
    return jsonify(result), 201
