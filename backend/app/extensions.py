"""Extensions Flask partagées par toute l'application."""
from flask_sqlalchemy import SQLAlchemy

# L'ORM : on manipule des objets Python, il écrit le SQL à notre place.
# Le même code fonctionne avec SQLite et PostgreSQL.
db = SQLAlchemy()
