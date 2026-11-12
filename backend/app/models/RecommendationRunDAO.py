from sqlalchemy.orm import sessionmaker

from app.models.base import get_engine
from app.models.RecommendationRun import RecommendationRun


class RecommendationRunORM:
    """
    DAO par orm pour le journal des recherches
    """

    def __init__(self, db_uri):
        self.db_uri = db_uri
        self.engine = get_engine(self.db_uri)
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def connect(self):
        return self.SessionFactory()

    def add(self, approach, objective, algo_ms, total_ms, result_count, corpus_size, query_text):
        """enregistre une recherche et retourne la ligne créée"""
        session = self.connect()
        try:
            run = RecommendationRun(
                approach=approach,
                objective=objective,
                algo_ms=algo_ms,
                total_ms=total_ms,
                result_count=result_count,
                corpus_size=corpus_size,
                query_text=query_text
            )
            session.add(run)
            session.commit()
            return run
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def findAll(self):
        """toutes les recherches, de la plus ancienne à la plus récente"""
        session = self.connect()
        try:
            return session.query(RecommendationRun).order_by(RecommendationRun.id).all()
        finally:
            session.close()
