"""Configuration de l'application, lue depuis les variables d'environnement."""
import os

# Origines du frontend autorisées en développement :
# 8080 = `python -m http.server 8080`, 5500 = extension Live Server de VS Code.
_DEFAULT_ORIGINS = (
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5500,http://127.0.0.1:5500"
)


class Config:
    # SQLite par défaut (fichier backend/instance/plante.db).
    # Avec Docker, DATABASE_URL pointe vers PostgreSQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///plante.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")
        if origin.strip()
    ]

    # Recommandation
    DEFAULT_TOP_K = 10
    MAX_TOP_K = 50

    # Approche embeddings : modèle de langage utilisé (nom sur Hugging Face).
    # Variante multilingue, plus lente mais qui comprend des mots-clés en
    # français : sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
    EMBEDDING_MODEL = os.environ.get(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    # Les tests remplacent le vrai modèle par une fonction légère (voir tests/).
    EMBEDDING_ENCODER = None

    # Catalogue
    DEFAULT_PER_PAGE = 24
    MAX_PER_PAGE = 100
