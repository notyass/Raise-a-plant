"""Critères de la recherche par environnement (objectif O2).

Ce fichier est la seule source de vérité pour les critères : le frontend
récupère cette liste via GET /api/options pour construire son formulaire.

Deux sortes de critères :
  - "slider" : un curseur de 0 à 100 (lumière, eau). Ses niveaux vont du
    plus bas au plus haut : ombre < mi-ombre < plein soleil ;
  - "choice" : un choix dans une liste (difficulté, saison, terre).

Chaque niveau ou choix a :
  - value       : le code, identique à ceux produits par normalizer.py ;
  - label       : le texte du formulaire ;
  - plant_label : le texte affiché sur une fiche de plante.
"""
from app.errors import ApiError

CRITERIA = {
    "sun": {
        "type": "slider",
        "label": "Lumière",
        "choices": [
            {"value": "shade", "label": "Ombre", "plant_label": "Ombre"},
            {"value": "partial_shade", "label": "Mi-ombre", "plant_label": "Mi-ombre"},
            {"value": "full_sun", "label": "Plein soleil", "plant_label": "Plein soleil"},
        ],
    },
    "water": {
        "type": "slider",
        "label": "Eau",
        "choices": [
            {"value": "low", "label": "Peu d'eau", "plant_label": "Peu d'eau"},
            {"value": "medium", "label": "Arrosage modéré", "plant_label": "Arrosage modéré"},
            {"value": "high", "label": "Beaucoup d'eau", "plant_label": "Beaucoup d'eau"},
        ],
    },
    "difficulty": {
        "type": "choice",
        "label": "Difficulté",
        "choices": [
            {"value": "easy", "label": "Facile", "plant_label": "Facile"},
            {"value": "moderate", "label": "Moyenne", "plant_label": "Moyenne"},
            {"value": "difficult", "label": "Difficile", "plant_label": "Difficile"},
        ],
    },
    "season": {
        "type": "choice",
        "label": "Saison",
        "choices": [
            {"value": "warm", "label": "Saison chaude (printemps-été)", "plant_label": "Saison chaude"},
            {"value": "cool", "label": "Saison fraîche (automne-début de printemps)", "plant_label": "Saison fraîche"},
            {"value": "year_round", "label": "Toute l'année", "plant_label": "Toute l'année"},
            {"value": "perennial", "label": "Vivace (repousse chaque année)", "plant_label": "Vivace"},
        ],
    },
    "soil": {
        "type": "choice",
        "label": "Terre",
        "choices": [
            {"value": "loam", "label": "Terre franche (limoneuse)", "plant_label": "Franche"},
            {"value": "sandy", "label": "Terre sableuse", "plant_label": "Sableuse"},
            {"value": "clay", "label": "Terre argileuse", "plant_label": "Argileuse"},
            {"value": "rich", "label": "Terre riche en matière organique", "plant_label": "Riche"},
            {"value": "well_drained", "label": "Terre bien drainée", "plant_label": "Bien drainée"},
        ],
    },
}

# Critères acceptés en plus des listes ci-dessus.
EXTRA_KEYS = {"category", "container"}
CONTAINER_LABEL = "Culture en pot"

# Importance de chaque critère, commune aux deux méthodes (choix de conception).
WEIGHTS = {
    "category": 3,
    "sun": 3,
    "water": 3,
    "difficulty": 2,
    "season": 2,
    "soil": 2,
    "container": 2,
}


def get_options():
    """Critères et choix possibles, pour le formulaire du frontend."""
    return CRITERIA


def _choice_for(key, value):
    """Renvoie le choix correspondant à un code, ou lève une erreur."""
    for choice in CRITERIA[key]["choices"]:
        if choice["value"] == value:
            return choice
    allowed = ", ".join(choice["value"] for choice in CRITERIA[key]["choices"])
    raise ApiError(f"Valeur inconnue pour « {key} » : {value!r}. Valeurs possibles : {allowed}.")


def level_position(key, code):
    """Position d'un code entre 0 et 1 dans l'ordre de ses choix.

    Exemple pour le soleil : shade -> 0, partial_shade -> 0.5, full_sun -> 1.
    C'est ce qui transforme un code en nombre pour la méthode vectorielle.
    """
    values = [choice["value"] for choice in CRITERIA[key]["choices"]]
    return values.index(code) / (len(values) - 1)


def codes_position(key, codes):
    """Position moyenne d'une liste de codes, ou None si la liste est vide.

    Exemple : ["partial_shade", "full_sun"] -> (0.5 + 1) / 2 = 0.75
    """
    if not codes:
        return None
    return sum(level_position(key, code) for code in codes) / len(codes)


def slider_choice(key, percent):
    """Niveau désigné par un curseur de 0 à 100.

    Le curseur est découpé en parts égales : avec 3 niveaux, 0-33 donne le
    premier, 34-66 le deuxième, 67-100 le troisième.
    """
    choices = CRITERIA[key]["choices"]
    index = min(len(choices) - 1, int(percent / 100 * len(choices)))
    return choices[index]


def codes_label(key, codes):
    """Libellé français d'une liste de codes d'une fiche.

    Exemples : codes_label("sun", ["partial_shade", "full_sun"])
               -> "Mi-ombre ou plein soleil"
               codes_label("soil", ["sandy", "rich", "well_drained"])
               -> "Sableuse, riche ou bien drainée"
    """
    labels = [
        choice["plant_label"]
        for choice in CRITERIA[key]["choices"]  # ordre du formulaire
        if choice["value"] in codes
    ]
    if not labels:
        return None
    # majuscule seulement au premier mot
    labels = [labels[0]] + [label[0].lower() + label[1:] for label in labels[1:]]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " ou " + labels[-1]


def clean_criteria(criteria):
    """Vérifie les critères reçus et enlève ceux qui sont vides."""
    if not isinstance(criteria, dict):
        raise ApiError("« criteria » doit être un objet JSON.")

    unknown = set(criteria) - set(CRITERIA) - EXTRA_KEYS
    if unknown:
        raise ApiError(f"Critère(s) inconnu(s) : {', '.join(sorted(unknown))}.")

    cleaned = {}
    for key, criterion in CRITERIA.items():
        value = criteria.get(key)
        if value in (None, ""):
            continue
        if criterion["type"] == "slider":
            is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
            if not is_number or not 0 <= value <= 100:
                raise ApiError(f"« {key} » doit être un nombre entre 0 et 100.")
        else:
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

    return cleaned


def build_query_parts(cleaned_criteria, category=None):
    """Découpe la demande par critère, à partir de critères déjà vérifiés.

    category : {"slug", "label"} de la catégorie choisie, ou None.

    Les deux méthodes reçoivent exactement cette liste. Chaque élément porte
    ce dont elles ont besoin :
        {"key": "sun",
         "code": "full_sun",     <- pour l'heuristique (règles SI... ALORS)
         "value": 0.8,           <- pour la méthode vectorielle (nombre entre 0 et 1)
         "label": "Lumière : plein soleil (80 %)"}   <- affiché à l'utilisateur
    """
    parts = []
    if category:
        parts.append({"key": "category", "code": category["slug"], "value": 1.0,
                      "label": f"Type : {category['label']}"})

    for key, criterion in CRITERIA.items():
        if key not in cleaned_criteria:
            continue
        if criterion["type"] == "slider":
            percent = cleaned_criteria[key]
            choice = slider_choice(key, percent)
            parts.append({
                "key": key,
                "code": choice["value"],
                "value": percent / 100,
                "label": f"{criterion['label']} : {choice['label'].lower()} ({round(percent)} %)",
            })
        else:
            choice = _choice_for(key, cleaned_criteria[key])
            parts.append({
                "key": key,
                "code": choice["value"],
                "value": level_position(key, choice["value"]),
                "label": f"{criterion['label']} : {choice['plant_label'].lower()}",
            })

    if cleaned_criteria.get("container"):
        parts.append({"key": "container", "code": True, "value": 1.0, "label": CONTAINER_LABEL})
    return parts


def describe_query(query_parts):
    """Résumé lisible de la demande : "Lumière : plein soleil (80 %) · Difficulté : facile"."""
    return " · ".join(part["label"] for part in query_parts)
