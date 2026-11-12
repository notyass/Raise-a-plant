"""Mixins : morceaux de comportement réutilisés par plusieurs modèles."""
from datetime import date, datetime, timezone

from ..extensions import db


def utcnow():
    """Date et heure courantes en UTC (sans fuseau, pour SQLite et PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    """Ajoute les colonnes created_at et updated_at à un modèle."""

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class SerializerMixin:
    """Ajoute to_dict() : transforme une ligne de la base en dictionnaire JSON."""

    def to_dict(self, exclude=()):
        data = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            data[column.name] = value
        return data
