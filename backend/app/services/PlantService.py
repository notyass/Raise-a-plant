from flask import current_app

from app.models.PlantDAO import PlantORM as PlantDAO
from app.services.care_guide import build_care
from app.services.document_builder import build_attributes
from app.services.query_builder import CRITERIA, codes_label


class PlantService:
    """Service des plantes et des catégories."""

    def __init__(self, db_uri=None):
        if db_uri is None:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        self.pdao = PlantDAO(db_uri=db_uri)

    def countPlants(self):
        """nombre de plantes en base"""
        return self.pdao.count()

    def getAllPlants(self):
        """toutes les plantes"""
        return self.pdao.findAll()

    def getPlantById(self, plant_id):
        """une plante par son id, ou None"""
        return self.pdao.findById(plant_id)

    def getPlantsByIds(self, plant_ids):
        """dictionnaire {id: plante} pour les id demandés"""
        return {plant.id: plant for plant in self.pdao.findByIds(plant_ids)}

    def getCategoryBySlug(self, slug):
        """une catégorie par son slug, ou None"""
        return self.pdao.findCategoryBySlug(slug)

    def getPlantIdsByCategory(self, slug):
        """ensemble des id des plantes d'une catégorie"""
        return self.pdao.findIdsByCategory(slug)

    def getCategories(self):
        """catégories avec le nombre de plantes de chacune"""
        categories = []
        for category, plant_count in self.pdao.findAllCategoriesWithCount():
            item = category.to_dict()
            item['plant_count'] = plant_count
            categories.append(item)
        return categories

    def getPlantsPage(self, category_slug=None, search=None, page=1, per_page=24):
        """page de la liste des plantes, avec filtres optionnels"""
        plants, total = self.pdao.findPage(
            category_slug=category_slug, search=search, page=page, per_page=per_page
        )
        return {
            'items': [PlantService.describePlant(plant) for plant in plants],
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': max(1, -(-total // per_page)),  # division arrondie au supérieur
        }

    @staticmethod
    def describePlant(plant, with_care=False):
        """fiche d'une plante pour l'API : ses colonnes, plus
        - 'labels' : libellés français de ses caractéristiques normalisées,
          par exemple {'sun': 'Mi-ombre ou plein soleil', 'difficulty': 'Facile'} ;
        - 'care' (si with_care) : les conseils d'entretien de sa page (O1)."""
        data = plant.to_dict()
        attributes = build_attributes(plant)
        data['labels'] = {key: codes_label(key, attributes[key]) for key in CRITERIA}
        if with_care:
            data['care'] = build_care(plant, attributes)
        return data
