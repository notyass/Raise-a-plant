"""Configuration de l'application, lue depuis les variables d'environnement."""
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Le dossier « instance » contient la base SQLite.
INSTANCE_DIR = os.path.join(BACKEND_DIR, 'instance')
DATABASE_PATH = os.path.join(INSTANCE_DIR, 'plante.db')

# Origines du frontend autorisées en développement :
# 8080 = `python -m http.server 8080`, 5500 = extension Live Server de VS Code.
_DEFAULT_ORIGINS = (
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5500,http://127.0.0.1:5500"
)


class Config:
    # SQLite par défaut (fichier backend/instance/plante.db).
    # Avec Docker, DATABASE_URL pointe vers PostgreSQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + DATABASE_PATH)

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get('CORS_ORIGINS', _DEFAULT_ORIGINS).split(',')
        if origin.strip()
    ]

    # Recommandation
    DEFAULT_TOP_K = 10
    MAX_TOP_K = 50

    # Catalogue
    DEFAULT_PER_PAGE = 24
    MAX_PER_PAGE = 100
