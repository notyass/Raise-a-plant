"""Petits outils de texte partagés par les deux méthodes."""
import re
import unicodedata


def simplify(text):
    """Met un texte en minuscules, sans accents ni ponctuation.

    Exemple : simplify("  Maïs 'Golden'  ") -> "mais golden"
    On compare ainsi « mais » et « Maïs » sans se soucier des accents.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()
