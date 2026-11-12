"""Gestion des erreurs : l'API répond toujours en JSON, même en cas d'erreur."""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Erreur métier levée par les services (ex. critère invalide)."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        # 404, 405, 400... levées par Flask lui-même.
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Erreur inattendue")
        return jsonify({"error": "Erreur interne du serveur."}), 500
