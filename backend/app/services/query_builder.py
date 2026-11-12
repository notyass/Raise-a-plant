"""Transforme les critères du formulaire en texte de requête.

Les données sont en anglais : chaque choix du formulaire (affiché en
français) est associé aux mots anglais qu'on cherchera dans les fiches.
Ce fichier est la seule source de vérité pour les critères : le frontend
récupère cette liste via GET /api/options pour construire son formulaire.
"""
from ..errors import ApiError

CRITERIA = {
    "sun": {
        "label": "Ensoleillement",
        "choices": [
            {"value": "full_sun", "label": "Plein soleil", "terms": "full sun"},
            {"value": "partial_shade", "label": "Mi-ombre", "terms": "partial shade"},
            {"value": "shade", "label": "Ombre", "terms": "full shade"},
        ],
    },
    "water": {
        "label": "Quantité d'eau",
        "choices": [
            {"value": "low", "label": "Peu d'eau", "terms": "low water drought tolerant"},
            {"value": "medium", "label": "Arrosage modéré", "terms": "moderate water 1 inch per week"},
            {"value": "high", "label": "Beaucoup d'eau", "terms": "high consistent moisture"},
        ],
    },
    "soil": {
        "label": "Type de terre",
        "choices": [
            {"value": "loam", "label": "Terre franche (limoneuse)", "terms": "loam"},
            {"value": "sandy", "label": "Terre sableuse", "terms": "sandy"},
            {"value": "clay", "label": "Terre argileuse", "terms": "clay"},
            {"value": "rich", "label": "Terre riche en matière organique", "terms": "rich organic matter"},
            {"value": "well_drained", "label": "Terre bien drainée", "terms": "well-drained"},
        ],
    },
    "season": {
        "label": "Saison",
        "choices": [
            {"value": "warm", "label": "Saison chaude (printemps-été)", "terms": "warm season"},
            {"value": "cool", "label": "Saison fraîche (automne-début de printemps)", "terms": "cool season"},
            {"value": "year_round", "label": "Toute l'année", "terms": "year round"},
            {"value": "perennial", "label": "Vivace (repousse chaque année)", "terms": "perennial"},
        ],
    },
    "difficulty": {
        "label": "Niveau",
        "choices": [
            {"value": "easy", "label": "Débutant", "terms": "easy"},
            {"value": "moderate", "label": "Intermédiaire", "terms": "moderate"},
            {"value": "difficult", "label": "Confirmé", "terms": "difficult"},
        ],
    },
}

# Critères acceptés en plus des listes ci-dessus.
EXTRA_KEYS = {"category", "container", "keywords"}
CONTAINER_TERMS = "container friendly"
CONTAINER_LABEL = "Culture en pot"
# Les critères sont séparés par une virgule dans le texte de requête.
QUERY_SEPARATOR = ", "
MAX_KEYWORDS_LENGTH = 200


def get_options():
    """Critères et choix possibles, pour le formulaire du frontend."""
    return CRITERIA


def _choice_for(key, value):
    """Renvoie le choix {"value", "label", "terms"} correspondant à une valeur."""
    for choice in CRITERIA[key]["choices"]:
        if choice["value"] == value:
            return choice
    allowed = ", ".join(choice["value"] for choice in CRITERIA[key]["choices"])
    raise ApiError(f"Valeur inconnue pour « {key} » : {value!r}. Valeurs possibles : {allowed}.")


def clean_criteria(criteria):
    """Vérifie les critères reçus et enlève ceux qui sont vides."""
    if not isinstance(criteria, dict):
        raise ApiError("« criteria » doit être un objet JSON.")

    unknown = set(criteria) - set(CRITERIA) - EXTRA_KEYS
    if unknown:
        raise ApiError(f"Critère(s) inconnu(s) : {', '.join(sorted(unknown))}.")

    cleaned = {}
    for key in CRITERIA:
        value = criteria.get(key)
        if value not in (None, ""):
            _choice_for(key, value)  # lève une erreur si la valeur est inconnue
            cleaned[key] = value

    category = criteria.get("category")
    if category not in (None, ""):
        if not isinstance(category, str):
            raise ApiError("« category » doit être un texte (slug de la catégorie).")
        cleaned["category"] = category.strip()

    container = criteria.get("container")
    if container not in (None, "", False):
        if container is not True:
            raise ApiError("« container » doit valoir true ou false.")
        cleaned["container"] = True

    keywords = criteria.get("keywords")
    if keywords not in (None, ""):
        if not isinstance(keywords, str):
            raise ApiError("« keywords » doit être un texte.")
        keywords = keywords.strip()[:MAX_KEYWORDS_LENGTH]
        if keywords:
            cleaned["keywords"] = keywords

    return cleaned


def build_query_parts(cleaned_criteria, category_name=None):
    """Découpe la requête par critère, à partir de critères déjà vérifiés.

    Chaque élément a un libellé français (affiché à l'utilisateur) et le texte
    anglais envoyé à l'algorithme :
        [{"label": "Plein soleil", "text": "full sun"}, ...]
    """
    parts = []
    if category_name:
        parts.append({"label": category_name, "text": category_name})
    for key in CRITERIA:
        if key in cleaned_criteria:
            choice = _choice_for(key, cleaned_criteria[key])
            parts.append({"label": choice["label"], "text": choice["terms"]})
    if cleaned_criteria.get("container"):
        parts.append({"label": CONTAINER_LABEL, "text": CONTAINER_TERMS})
    if cleaned_criteria.get("keywords"):
        parts.append({"label": cleaned_criteria["keywords"], "text": cleaned_criteria["keywords"]})
    return parts


def build_query_text(cleaned_criteria, category_name=None):
    """Assemble le texte de requête complet.

    Exemple : {"sun": "full_sun", "difficulty": "easy"} -> "full sun, easy"
    Les deux approches reçoivent exactement ce même texte : la comparaison
    porte donc sur les algorithmes, pas sur la formulation de la demande.
    """
    parts = build_query_parts(cleaned_criteria, category_name=category_name)
    return QUERY_SEPARATOR.join(part["text"] for part in parts)
