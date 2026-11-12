"""Accès aux plantes et aux catégories (toutes les requêtes SQL sont ici)."""
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Category, Plant


def count_plants():
    return db.session.scalar(db.select(db.func.count(Plant.id))) or 0


def get_all_plants():
    """Toutes les plantes avec leur catégorie (sert à construire l'index)."""
    statement = db.select(Plant).options(joinedload(Plant.category)).order_by(Plant.id)
    return db.session.scalars(statement).all()


def get_plant(plant_id):
    return db.session.get(Plant, plant_id)


def get_plants_by_ids(plant_ids):
    """Renvoie un dictionnaire {id: plante} pour les identifiants demandés."""
    if not plant_ids:
        return {}
    statement = (
        db.select(Plant)
        .options(joinedload(Plant.category))
        .where(Plant.id.in_(list(plant_ids)))
    )
    return {plant.id: plant for plant in db.session.scalars(statement).all()}


def get_category(slug):
    return db.session.scalar(db.select(Category).where(Category.slug == slug))


def get_plant_ids_by_category(slug):
    """Identifiants des plantes d'une catégorie (filtre de la recommandation)."""
    statement = (
        db.select(Plant.id)
        .join(Category, Plant.category_id == Category.id)
        .where(Category.slug == slug)
    )
    return set(db.session.scalars(statement).all())


def list_categories():
    """Catégories avec le nombre de plantes de chacune."""
    statement = (
        db.select(Category, db.func.count(Plant.id))
        .select_from(Category)
        .outerjoin(Plant, Plant.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    categories = []
    for category, plant_count in db.session.execute(statement).all():
        item = category.to_dict()
        item["plant_count"] = plant_count
        categories.append(item)
    return categories


def list_plants(category_slug=None, search=None, page=1, per_page=24):
    """Liste paginée des plantes pour le catalogue."""
    conditions = []
    if category_slug:
        conditions.append(Category.slug == category_slug)
    if search:
        conditions.append(Plant.name.ilike(f"%{search}%"))

    # Deux requêtes avec les mêmes filtres : le total, puis la page demandée.
    count_statement = (
        db.select(db.func.count(Plant.id))
        .select_from(Plant)
        .join(Category, Plant.category_id == Category.id)
    )
    page_statement = (
        db.select(Plant)
        .join(Category, Plant.category_id == Category.id)
        .options(joinedload(Plant.category))
    )
    for condition in conditions:
        count_statement = count_statement.where(condition)
        page_statement = page_statement.where(condition)

    total = db.session.scalar(count_statement) or 0
    plants = db.session.scalars(
        page_statement.order_by(Plant.name, Plant.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()

    return {
        "items": [plant.to_dict() for plant in plants],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, -(-total // per_page)),  # division arrondie au supérieur
    }
