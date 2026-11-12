"""Images des plantes : quel titre chercher sur Wikipédia pour une plante.

Les photos sont récupérées par le script prepa_images.py à partir du nom
latin. Ce module ne fait aucun appel réseau : il contient seulement la
règle qui donne le titre de page à partir du nom latin.
"""
import re

# « Genre espèce », éventuellement avec un signe d'hybride (x ou ×).
BINOMIAL = re.compile(r"^([A-Z][a-z-]+)\s+(?:[x×]\s+)?([a-z-]+)")
GENUS = re.compile(r"^([A-Z][a-z-]+)")


def lookup_title(scientific_name):
    """Titre de la page Wikipédia à chercher pour un nom latin, ou None.

    On garde le genre et l'espèce, sans la variété ni le cultivar :
        "Solanum lycopersicum 'Tiny Tim'" -> "Solanum lycopersicum"
        "Brassica oleracea var. botrytis" -> "Brassica oleracea"
        "Rosa 'Eden'"                     -> "Rosa"
    """
    if not scientific_name:
        return None
    match = BINOMIAL.match(scientific_name.strip())
    if match and match.group(2) not in ("var", "subsp", "x"):
        return f"{match.group(1)} {match.group(2)}"
    match = GENUS.match(scientific_name.strip())
    return match.group(1) if match else None
