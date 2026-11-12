from flask import Blueprint, current_app, jsonify, request

from app.errors import ApiError
from app.services import query_builder
from app.services.RecommendationService import RecommendationService
from app.services.recommenders import DEFAULT_APPROACH, OBJECTIVES

recommendations_bp = Blueprint('recommendations', __name__)


def _read_payload():
    """lit le corps JSON et en tire (corps, méthode, nombre de résultats)"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("Le corps de la requête doit être un objet JSON.")

    top_k = payload.get('top_k', current_app.config['DEFAULT_TOP_K'])
    max_top_k = current_app.config['MAX_TOP_K']
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= max_top_k:
        raise ApiError(f"« top_k » doit être un entier entre 1 et {max_top_k}.")

    approach = payload.get('approach', DEFAULT_APPROACH)
    if not isinstance(approach, str):
        raise ApiError("« approach » doit être un texte.")

    return payload, approach, top_k


@recommendations_bp.route('/options', methods=['GET'])
def options():
    """critères du formulaire O2 et leurs choix"""
    return jsonify(query_builder.get_options())


@recommendations_bp.route('/approaches', methods=['GET'])
def approaches():
    """les deux méthodes et les deux objectifs"""
    rs = RecommendationService()
    return jsonify({'items': rs.describeApproaches(), 'objectives': OBJECTIVES})


@recommendations_bp.route('/searches', methods=['POST'])
def search():
    """O1 : retrouve une plante à partir de son nom

    corps JSON attendu :
        {"query": "tomate", "approach": "heuristic", "top_k": 10}
    """
    payload, approach, top_k = _read_payload()
    rs = RecommendationService()
    result = rs.search(query=payload.get('query'), approach=approach, top_k=top_k)
    return jsonify(result), 201


@recommendations_bp.route('/recommendations', methods=['POST'])
def recommend():
    """O2 : propose des plantes pour un environnement

    corps JSON attendu (sun et water : curseurs de 0 à 100) :
        {"criteria": {"sun": 80, "water": 30, "difficulty": "easy"},
         "approach": "vector", "top_k": 10}
    """
    payload, approach, top_k = _read_payload()
    rs = RecommendationService()
    result = rs.recommend(criteria=payload.get('criteria', {}), approach=approach, top_k=top_k)
    return jsonify(result), 201
