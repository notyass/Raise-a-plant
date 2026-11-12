"""Journal des recommandations : une ligne par recommandation calculée.

C'est cette table qui permet d'afficher les temps de réponse min, max et
moyen dans le tableau de bord, et plus tard de comparer les deux approches.
"""
from ..extensions import db
from .mixins import SerializerMixin, TimestampMixin


class RecommendationRun(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "recommendation_runs"

    id = db.Column(db.Integer, primary_key=True)
    approach = db.Column(db.String(40), nullable=False, index=True)
    # Temps du calcul de recommandation seul (vectorisation + similarité + tri).
    algo_ms = db.Column(db.Float, nullable=False)
    # Temps total côté serveur (calcul + lectures en base).
    total_ms = db.Column(db.Float, nullable=False)
    result_count = db.Column(db.Integer, nullable=False)
    corpus_size = db.Column(db.Integer, nullable=False)
    query_text = db.Column(db.Text)
