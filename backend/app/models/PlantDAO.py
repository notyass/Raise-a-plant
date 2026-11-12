from sqlalchemy import func
from sqlalchemy.orm import joinedload, sessionmaker

from app.models.base import get_engine
from app.models.Category import Category
from app.models.Plant import Plant
from app.models.PlantDAOInterface import PlantDAOInterface


class PlantORM(PlantDAOInterface):
    """DAO par orm pour les plantes et leurs catégories.
    Toutes les requêtes sur ces deux tables sont ici.
    """

    def __init__(self, db_uri):
        self.db_uri = db_uri
        self.engine = get_engine(self.db_uri)
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def connect(self):
        """retourne une nouvelle session orm"""
        return self.SessionFactory()

    def _query_with_category(self, session):
        """prépare la requête de base en préchargeant la catégorie par joinedload :
        une plante reste ainsi utilisable (plant.category) une fois la session fermée"""
        return session.query(Plant).options(joinedload(Plant.category))

    def count(self):
        """nombre de plantes en base"""
        session = self.connect()
        try:
            return session.query(func.count(Plant.id)).scalar() or 0
        finally:
            session.close()

    def findAll(self):
        """retourne toutes les plantes (sert à construire les index de recommandation)"""
        session = self.connect()
        try:
            return self._query_with_category(session).order_by(Plant.id).all()
        finally:
            session.close()

    def findById(self, id):
        """retourne la plante, ou None si non trouvée"""
        session = self.connect()
        try:
            return self._query_with_category(session).filter(Plant.id == id).first()
        finally:
            session.close()

    def findByIds(self, ids):
        """retourne les plantes dont l'id est dans la liste"""
        ids = list(ids)
        if not ids:
            return []
        session = self.connect()
        try:
            return self._query_with_category(session).filter(Plant.id.in_(ids)).all()
        finally:
            session.close()

    def findPage(self, category_slug=None, search=None, page=1, per_page=24):
        """retourne (plantes de la page, nombre total de plantes correspondant aux filtres)"""
        filters = []
        if category_slug:
            filters.append(Category.slug == category_slug)
        if search:
            filters.append(Plant.name.ilike(f"%{search}%"))

        session = self.connect()
        try:
            total = (
                session.query(func.count(Plant.id))
                .join(Category, Plant.category_id == Category.id)
                .filter(*filters)
                .scalar()
            ) or 0
            plants = (
                self._query_with_category(session)
                .join(Category, Plant.category_id == Category.id)
                .filter(*filters)
                .order_by(Plant.name, Plant.id)
                .limit(per_page)
                .offset((page - 1) * per_page)
                .all()
            )
            return plants, total
        finally:
            session.close()

    def findIdsByCategory(self, category_slug):
        """retourne l'ensemble des id des plantes d'une catégorie"""
        session = self.connect()
        try:
            rows = (
                session.query(Plant.id)
                .join(Category, Plant.category_id == Category.id)
                .filter(Category.slug == category_slug)
                .all()
            )
            return {row[0] for row in rows}
        finally:
            session.close()

    def findCategoryBySlug(self, slug):
        """retourne la catégorie, ou None si non trouvée"""
        session = self.connect()
        try:
            return session.query(Category).filter(Category.slug == slug).first()
        finally:
            session.close()

    def findAllCategoriesWithCount(self):
        """retourne une liste de couples (catégorie, nombre de plantes)"""
        session = self.connect()
        try:
            rows = (
                session.query(Category, func.count(Plant.id))
                .outerjoin(Plant, Plant.category_id == Category.id)
                .group_by(Category.id)
                .order_by(Category.name)
                .all()
            )
            return [(row[0], row[1]) for row in rows]
        finally:
            session.close()
