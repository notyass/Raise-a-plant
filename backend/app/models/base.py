"""Base commune des modèles ORM, mixins et moteur SQLAlchemy."""
import threading
from datetime import date, datetime, timezone

from sqlalchemy import Column, DateTime, create_engine
from sqlalchemy.orm import declarative_base

# Base déclarative partagée par tous les modèles ORM
Base = declarative_base()


def utcnow():
    """Date et heure courantes en UTC (sans fuseau, pour SQLite et PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BaseModelMixin:
    """
    Mixin fournissant des méthodes pratiques pour les modèles ORM :
    - accès dictionnaire via __getitem__ : plant['name'] comme plant.name
    - méthode to_dict() pour la sérialisation en JSON
    """

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(f"L'objet '{self.__class__.__name__}' n'a pas l'attribut '{item}'")

    def to_dict(self):
        """retourne les colonnes de l'objet sous forme de dictionnaire"""
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, (datetime, date)):
                val = val.isoformat()
            result[col.name] = val
        return result


class TimestampMixin:
    """Mixin ajoutant les colonnes created_at et updated_at à un modèle."""

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# Un moteur par base de données, créé une seule fois puis réutilisé :
# un moteur garde des connexions ouvertes, en recréer un à chaque requête
# gaspillerait du temps et des connexions (surtout avec PostgreSQL).
_engines = {}
_engines_lock = threading.Lock()


def get_engine(db_uri):
    """Retourne le moteur SQLAlchemy de la base db_uri."""
    with _engines_lock:
        if db_uri not in _engines:
            _engines[db_uri] = create_engine(db_uri, echo=False)
        return _engines[db_uri]


def dispose_engines():
    """Ferme toutes les connexions (utilisé par les tests)."""
    with _engines_lock:
        for engine in _engines.values():
            engine.dispose()
        _engines.clear()
