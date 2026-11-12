"""Conseils d'entretien d'une plante (objectif O1).

La page d'une plante est générée à partir de la base : ses
caractéristiques normalisées (codes) sont transformées en conseils rédigés
en français. Le texte d'origine du jeu de données, plus précis mais en
anglais, est joint à chaque conseil.
"""

# Pour chaque critère : son titre, la colonne d'origine et un conseil par code.
ADVICE = {
    "sun": {
        "title": "Lumière",
        "source": "sun_requirement",
        "codes": {
            "full_sun": "Installe-la au soleil direct, au moins 6 heures par jour.",
            "partial_shade": "Elle se plaît à mi-ombre : du soleil le matin, de l'ombre aux heures chaudes.",
            "shade": "Garde-la à l'ombre, sans soleil direct.",
        },
    },
    "water": {
        "title": "Arrosage",
        "source": "water_requirement",
        "codes": {
            "low": "Arrose peu : laisse la terre sécher entre deux arrosages.",
            "medium": "Arrose régulièrement, environ 2 à 3 cm d'eau par semaine.",
            "high": "Garde la terre toujours humide, sans la détremper.",
        },
    },
    "soil": {
        "title": "Terre",
        "source": "soil_type",
        "codes": {
            "loam": "Elle aime une terre franche, ni trop lourde ni trop légère.",
            "sandy": "Une terre légère et sableuse lui convient.",
            "clay": "Elle supporte une terre argileuse.",
            "rich": "Donne-lui une terre riche : ajoute du compost.",
            "well_drained": "La terre doit être bien drainée : l'eau ne doit pas stagner.",
        },
    },
    "season": {
        "title": "Saison",
        "source": "growing_season",
        "codes": {
            "warm": "Elle pousse à la saison chaude : sème ou plante au printemps, après les dernières gelées.",
            "cool": "Elle préfère la fraîcheur : sème au début du printemps ou en fin d'été.",
            "year_round": "Elle se cultive toute l'année, en intérieur ou sous climat doux.",
            "perennial": "C'est une vivace : elle repousse chaque année.",
        },
    },
    "difficulty": {
        "title": "Difficulté",
        "source": "growing_difficulty",
        "codes": {
            "easy": "Culture facile : un bon choix pour débuter.",
            "moderate": "Elle demande un peu d'attention et de régularité.",
            "difficult": "Culture délicate, plutôt pour un jardinier confirmé.",
        },
    },
}

CONTAINER_ADVICE = "Elle peut pousser en pot, sur un balcon ou une terrasse."


def build_care(plant, attributes):
    """Liste des conseils d'entretien d'une plante.

    plant      : la plante (objet Plant ou équivalent) ;
    attributes : ses caractéristiques normalisées (document_builder.build_attributes).

    Chaque conseil : {"key", "title", "advice": [phrases], "detail": texte d'origine}.
    """
    care = []
    for key, entry in ADVICE.items():
        sentences = [
            sentence
            for code, sentence in entry["codes"].items()  # ordre du barème
            if code in attributes.get(key, [])
        ]
        detail = getattr(plant, entry["source"], None)
        if not sentences and not detail:
            continue  # la fiche ne dit rien sur ce critère
        care.append({"key": key, "title": entry["title"], "advice": sentences, "detail": detail})

    if attributes.get("container"):
        care.append({"key": "container", "title": "Culture en pot", "advice": [CONTAINER_ADVICE], "detail": None})
    return care
