"""Faux encodeur pour les tests : remplace le modèle de langage.

Chaque mot allume une case d'un vecteur de 256 cases (choisie par un
hachage stable). Ce n'est pas un vrai embedding (il ne comprend pas le
sens), mais il respecte le même contrat : liste de textes -> tableau de
vecteurs. Cela permet de tester toute la mécanique sans télécharger de modèle.
"""
import re
import zlib

import numpy as np

DIMENSIONS = 256


def fake_encoder(texts):
    vectors = np.zeros((len(texts), DIMENSIONS), dtype=np.float32)
    for row, text in enumerate(texts):
        for word in re.findall(r"[a-z]+", text.lower()):
            vectors[row, zlib.crc32(word.encode("utf-8")) % DIMENSIONS] += 1.0
    return vectors
