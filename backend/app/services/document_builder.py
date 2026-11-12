"""Construit le « document » texte d'une plante.

Les deux approches de recommandation (TF-IDF, puis embeddings en V2)
travaillent sur du texte. On regroupe donc les champs utiles d'une plante
dans un seul texte : c'est ce texte qui sera comparé à la requête.
"""

# Champs texte de la plante recopiés dans le document, dans cet ordre.
TEXT_FIELDS = (
    "name",
    "scientific_name",
    "description",
    "sun_requirement",
    "water_requirement",
    "soil_type",
    "growing_difficulty",
    "growing_season",
    "sowing_method",
    "flavor_profile",
    "culinary_uses",
)


def build_document(plant):
    """Renvoie le texte décrivant une plante (objet Plant ou équivalent)."""
    parts = []

    category = getattr(plant, "category", None)
    if category is not None:
        parts.append(category.name)

    for field in TEXT_FIELDS:
        value = getattr(plant, field, None)
        if value:
            parts.append(str(value))

    # Les booléens deviennent des mots, sinon ils seraient invisibles.
    if getattr(plant, "is_container_friendly", False):
        parts.append("container friendly")
    if getattr(plant, "is_heirloom", False):
        parts.append("heirloom")

    return ". ".join(parts)
