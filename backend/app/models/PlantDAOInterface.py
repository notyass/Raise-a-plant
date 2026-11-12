
class PlantDAOInterface:
    """Liste des opérations qu'un DAO de plantes doit fournir.
    Les services ne dépendent que de cette interface : on pourrait changer
    de technologie de stockage sans les modifier.
    """

    def connect(self):
        """retourne une session de connexion ORM"""
        pass

    def count(self):
        """nombre de plantes en base"""
        pass

    def findAll(self):
        """trouve toutes les plantes"""
        pass

    def findById(self, id):
        """trouve une plante par son id"""
        pass

    def findByIds(self, ids):
        """trouve les plantes dont l'id est dans la liste"""
        pass

    def findPage(self, category_slug=None, search=None, page=1, per_page=24):
        """trouve une page de plantes, avec filtres optionnels"""
        pass

    def findIdsByCategory(self, category_slug):
        """trouve les id des plantes d'une catégorie"""
        pass

    def findCategoryBySlug(self, slug):
        """trouve une catégorie par son slug"""
        pass

    def findAllCategoriesWithCount(self):
        """trouve toutes les catégories avec leur nombre de plantes"""
        pass
