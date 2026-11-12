"""Normalisation des données à l'import.

Le jeu de données décrit le soleil, l'eau, la terre, la saison et la
difficulté en texte libre anglais, avec des centaines de formulations
différentes (« Full sun (6+ hours) », « 1 inch per week, drought tolerant
once established »...). On ramène chaque texte à une petite liste de codes
(« full_sun », « low »...) grâce à des règles de mots-clés.

Ces codes servent à deux choses :
  - la méthode heuristique compare directement les codes aux critères ;
  - l'interface affiche leur libellé français à la place du texte anglais.

Une plante peut avoir plusieurs codes pour un même critère : « Full sun to
partial shade » donne ["full_sun", "partial_shade"].
"""
import re

# Nom français de chaque type de plante (clé = « slug » du jeu de données).
CATEGORY_NAMES_FR = {
    'allium': "Alliacées (ail, oignon)",
    'bean': "Haricots et légumineuses",
    'berry': "Petits fruits et baies",
    'brassica': "Choux (brassicacées)",
    'corn': "Maïs",
    'cucumber': "Concombres",
    'eggplant': "Aubergines",
    'flower': "Fleurs",
    'fruit-tree': "Arbres fruitiers",
    'grass': "Graminées et bambous",
    'ground-cover': "Couvre-sols",
    'herb': "Herbes aromatiques",
    'houseplant': "Plantes d'intérieur",
    'lettuce': "Laitues et salades",
    'melon': "Melons",
    'microgreen': "Micro-pousses",
    'native-wildflower': "Fleurs sauvages indigènes",
    'nut-tree': "Arbres à fruits à coque",
    'ornamental-tree': "Arbres d'ornement",
    'pea': "Pois",
    'pepper': "Poivrons et piments",
    'root-vegetable': "Légumes-racines",
    'rose': "Rosiers",
    'shade-tree': "Arbres d'ombrage",
    'shrub': "Arbustes et haies",
    'squash': "Courges",
    'succulent': "Succulentes et cactus",
    'tomato': "Tomates",
    'tropical': "Plantes tropicales",
    'vine': "Plantes grimpantes",
}

# Règles : pour chaque critère, une liste (code, expression régulière).
# Un code est retenu si son expression est trouvée dans le texte en minuscules.
RULES = {
    'sun': [
        ('full_sun', r"full sun|direct sun"),
        ('partial_shade', r"partial|part shade|part sun|dappled|indirect|moderate light|bright light|indoor"),
        ('shade', r"full shade"),
    ],
    'water': [
        ('low', r"\blow\b|minimal|infrequent|sparingly|drought"),
        ('medium', r"moderate|regular|average|medium|\b1 inch|1-1\.5 inch|when top|even moisture|evenly moist"),
        ('high', r"\bhigh\b|heavy|abundant|constant|1-2 inch|1\.5-2 inch|\b2 inch|2-3 inch|\bwet\b|mist"),
    ],
    'soil': [
        ('loam', r"loam"),
        ('sandy', r"sand"),
        ('clay', r"clay"),
        ('rich', r"rich|fertile|organic|compost|humus"),
        ('well_drained', r"well-drained|well drained|draining|good drainage"),
    ],
    'season': [
        ('warm', r"warm|summer|june|july|august"),
        ('cool', r"cool|fall|autumn|winter|frost"),
        ('year_round', r"year-round|year round|indoor"),
        ('perennial', r"perennial|evergreen|deciduous|tree|shrub"),
    ],
    'difficulty': [
        ('easy', r"easy"),
        ('moderate', r"moderate"),
        ('difficult', r"difficult|challenging|advanced"),
    ],
}

# Colonne du jeu de données lue pour chaque critère.
SOURCE_COLUMNS = {
    'sun': 'sun_requirement',
    'water': 'water_requirement',
    'soil': 'soil_type',
    'season': 'growing_season',
    'difficulty': 'growing_difficulty',
}


def normalize(key, text):
    """Retourne la liste des codes du critère `key` trouvés dans `text`.

    Exemple : normalize('sun', 'Full sun to partial shade (4-6+ hours)')
              -> ['full_sun', 'partial_shade']
    """
    if not text:
        return []
    lowered = text.lower()
    codes = [code for code, pattern in RULES[key] if re.search(pattern, lowered)]

    if key == 'water' and not codes and re.search(r"moist|consistent|inch", lowered):
        codes = ['medium']  # arrosage décrit sans mot-clé net : on retient « modéré »

    if key == 'season':
        # « Spring » seul (ni été ni automne) : semis possible dans les deux saisons.
        if not {'warm', 'cool'} & set(codes) and 'spring' in lowered:
            codes = ['warm', 'cool'] + codes
        # « Spring through fall » couvre aussi l'été.
        if 'warm' not in codes and re.search(r"spring (through|to)|spring, summer", lowered):
            codes = ['warm'] + codes

    return codes


def codes_to_text(codes):
    """['full_sun', 'partial_shade'] -> 'full_sun,partial_shade' (stocké en base)."""
    return ','.join(codes) if codes else None


def text_to_codes(text):
    """'full_sun,partial_shade' -> ['full_sun', 'partial_shade']."""
    return text.split(',') if text else []


def category_name_fr(slug, default=None):
    """Nom français d'une catégorie, ou `default` si le slug est inconnu."""
    return CATEGORY_NAMES_FR.get(slug, default)
