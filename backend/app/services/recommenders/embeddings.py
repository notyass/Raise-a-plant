"""Approche n°2 : embeddings + similarité cosinus.

Idée : un modèle de langage transforme un texte en un vecteur dense
(384 nombres avec le modèle par défaut) qui représente son SENS. Deux
textes qui parlent de la même chose ont des vecteurs proches, même sans
aucun mot en commun (« drought tolerant » et « needs little water »).
On transforme chaque fiche en vecteur une fois pour toutes, puis la requête,
et on classe les fiches par similarité cosinus, comme pour TF-IDF.

Différences avec TF-IDF : les vecteurs sont denses (aucun zéro) et petits,
mais les calculer demande un modèle de langage, bien plus lourd.
"""
import hashlib
import importlib.util
import os
import time

import numpy as np

from .base import BaseRecommender, Recommendation

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_EXPLANATION_TERMS = 5


class SentenceTransformerEncoder:
    """Encodeur par défaut : un modèle chargé avec la bibliothèque sentence-transformers.

    Un encodeur est simplement une fonction : liste de textes -> tableau de
    vecteurs (une ligne par texte). Les tests en utilisent un faux, plus léger.
    """

    def __init__(self, model_name):
        self.model_name = model_name
        self.load_duration_ms = None
        self._model = None

    def __call__(self, texts):
        if self._model is None:
            start = time.perf_counter()
            # Import tardif : la bibliothèque est lourde (elle charge PyTorch).
            from sentence_transformers import SentenceTransformer

            # Le modèle est téléchargé depuis Hugging Face au premier usage.
            self._model = SentenceTransformer(self.model_name)
            self.load_duration_ms = (time.perf_counter() - start) * 1000
        return self._model.encode(
            list(texts), batch_size=32, show_progress_bar=False, convert_to_numpy=True
        )


class EmbeddingRecommender(BaseRecommender):
    key = "embeddings"
    label = "Embeddings + cosinus"
    description = (
        "Un modèle de langage transforme chaque fiche en vecteur dense qui "
        "représente son sens. On classe les fiches par similarité cosinus "
        "avec le vecteur de la requête."
    )
    explanation = (
        "Proximité de sens entre chaque critère de ta demande et sa fiche "
        "(cosinus : plus il est proche de 1, plus c'est proche)."
    )
    complexity = {
        "notation": (
            "N = nombre de fiches, d = dimension des vecteurs, C = coût d'un "
            "passage de texte dans le modèle de langage (ne dépend pas de N)"
        ),
        "indexation": "O(N × C) la première fois, puis simple relecture du fichier de vecteurs en O(N × d)",
        "requete": (
            "O(C) pour encoder la requête + O(N × d) pour le produit "
            "matrice-vecteur + O(N log N) pour le tri complet"
        ),
        "memoire": "O(N × d) pour la matrice dense + les poids du modèle (taille fixe)",
        "pistes": (
            "Recherche approximative des plus proches voisins (index HNSW, FAISS) ; "
            "sélection des k meilleurs sans trier les N scores ; vecteurs "
            "compressés ; mémorisation des requêtes fréquentes."
        ),
    }

    def __init__(self, model_name=DEFAULT_MODEL, encoder=None, cache_dir=None):
        """
        model_name : nom du modèle sur Hugging Face.
        encoder    : fonction textes -> vecteurs ; par défaut, le vrai modèle.
        cache_dir  : dossier où garder les vecteurs des fiches, ou None.
        """
        self.model_name = model_name
        self.encoder = encoder or SentenceTransformerEncoder(model_name)
        self.cache_dir = cache_dir
        self.matrix = None  # matrice dense N × d, lignes de norme 1
        self.plant_ids = np.array([], dtype=int)
        self.fit_duration_ms = None
        self.loaded_from_cache = False

    @classmethod
    def unavailable_reason(cls):
        if importlib.util.find_spec("sentence_transformers") is None:
            return (
                "La bibliothèque sentence-transformers n'est pas installée. "
                "Dans le dossier backend : pip install -r requirements-embeddings.txt"
            )
        return None

    # ----- Encodage -----

    def _encode(self, texts):
        """Encode des textes et ramène chaque vecteur à une norme de 1."""
        vectors = np.asarray(self.encoder(texts), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # évite une division par zéro
        return vectors / norms

    # ----- Index -----

    def fit(self, documents):
        start = time.perf_counter()
        self.plant_ids = np.array([doc.plant_id for doc in documents], dtype=int)
        texts = [doc.text for doc in documents]

        # Encoder toutes les fiches est l'étape la plus longue : on garde le
        # résultat sur le disque pour ne pas recommencer à chaque démarrage.
        cache_path = self._cache_path(texts)
        matrix = self._load_cache(cache_path, expected_rows=len(texts))
        self.loaded_from_cache = matrix is not None
        if matrix is None:
            matrix = self._encode(texts)
            self._save_cache(cache_path, matrix)
        self.matrix = matrix

        # Charge le modèle dès maintenant si ce n'est pas déjà fait, pour que
        # la première recommandation ne paie pas le temps de chargement.
        self._encode(["warm up"])
        self.fit_duration_ms = (time.perf_counter() - start) * 1000

    def _cache_path(self, texts):
        """Chemin du fichier de vecteurs, propre au modèle et aux textes."""
        if not self.cache_dir:
            return None
        digest = hashlib.sha256(self.model_name.encode("utf-8"))
        for text in texts:
            digest.update(b"\x00" + text.encode("utf-8"))
        return os.path.join(self.cache_dir, f"embeddings_{digest.hexdigest()[:16]}.npy")

    @staticmethod
    def _load_cache(cache_path, expected_rows):
        if not cache_path or not os.path.exists(cache_path):
            return None
        try:
            matrix = np.load(cache_path, allow_pickle=False)
        except (OSError, ValueError):
            return None  # fichier illisible : on recalcule
        if matrix.ndim != 2 or matrix.shape[0] != expected_rows:
            return None
        return matrix.astype(np.float32, copy=False)

    @staticmethod
    def _save_cache(cache_path, matrix):
        if not cache_path:
            return
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            np.save(cache_path, matrix)
        except OSError:
            pass  # pas grave : on recalculera au prochain démarrage

    # ----- Recommandation -----

    def recommend(self, query_text, top_k=10, allowed_ids=None, query_parts=None):
        if self.matrix is None:
            raise RuntimeError("L'index n'est pas construit : appeler fit() d'abord.")
        parts = query_parts or []

        # 1. Un seul appel au modèle pour la requête entière et pour chaque
        #    critère (les critères servent à l'explication).
        vectors = self._encode([query_text] + [part["text"] for part in parts])
        query_vector, part_vectors = vectors[0], vectors[1:]

        # 2. Similarité cosinus : vecteurs de norme 1, donc un produit
        #    matrice × vecteur donne les N scores (entre -1 et 1).
        scores = self.matrix @ query_vector

        # 3. Filtre optionnel (ex. une seule catégorie).
        if allowed_ids is not None:
            allowed = np.isin(self.plant_ids, list(allowed_ids))
            scores = np.where(allowed, scores, -np.inf)

        # 4. Tri de tous les scores (V1, non optimisé). Contrairement à TF-IDF,
        #    toutes les fiches ont un score : il y a toujours top_k résultats.
        order = np.argsort(-scores, kind="stable")

        results = []
        for row in order[:top_k]:
            if not np.isfinite(scores[row]):
                break  # fiches exclues par le filtre
            results.append(
                Recommendation(
                    plant_id=int(self.plant_ids[row]),
                    score=float(scores[row]),
                    matched_terms=self._explain(parts, part_vectors, row),
                )
            )
        return results

    def _explain(self, parts, part_vectors, row):
        """Critères de la demande les plus proches de la fiche.

        Un embedding ne permet pas de dire quel mot a compté. On compare donc
        le vecteur de chaque critère (« full sun », « easy »...) à celui de la
        fiche : les critères au cosinus le plus élevé sont ceux que la fiche
        satisfait le mieux, au sens du modèle.
        """
        if not parts:
            return []
        similarities = part_vectors @ self.matrix[row]
        ranked = sorted(zip(parts, similarities), key=lambda pair: -pair[1])
        return [
            {"term": part["label"], "weight": round(float(similarity), 4)}
            for part, similarity in ranked[:MAX_EXPLANATION_TERMS]
        ]

    def index_stats(self):
        if self.matrix is None:
            return None
        stats = {
            "model_name": self.model_name,
            "documents": int(self.matrix.shape[0]),
            "dimensions": int(self.matrix.shape[1]),
            "matrix_memory_kb": round(self.matrix.nbytes / 1024, 1),
            "fit_duration_ms": round(self.fit_duration_ms, 2),
            "loaded_from_cache": self.loaded_from_cache,
        }
        load_duration_ms = getattr(self.encoder, "load_duration_ms", None)
        if load_duration_ms is not None:
            stats["model_load_ms"] = round(load_duration_ms, 2)
        return stats
