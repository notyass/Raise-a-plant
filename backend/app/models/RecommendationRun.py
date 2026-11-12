from sqlalchemy import Column, Float, Integer, String, Text

from app.models.base import Base, BaseModelMixin, TimestampMixin


class RecommendationRun(Base, BaseModelMixin, TimestampMixin):
    """model du journal des recherches : une ligne par recherche calculée
    C'est cette table qui permet d'afficher les temps de réponse min, max et
    moyen de chaque méthode, pour chaque objectif, dans le tableau de bord.
    """
    __tablename__ = 'recommendation_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    approach = Column(String(40), nullable=False, index=True)  # "heuristic" ou "vector"
    objective = Column(String(40), nullable=False, index=True)  # "care" (O1) ou "environment" (O2)
    # temps du calcul de la méthode seul (scores + tri + explication)
    algo_ms = Column(Float, nullable=False)
    # temps total côté serveur (calcul + lectures en base)
    total_ms = Column(Float, nullable=False)
    result_count = Column(Integer, nullable=False)
    corpus_size = Column(Integer, nullable=False)
    query_text = Column(Text, nullable=True)
