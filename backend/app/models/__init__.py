"""Modèles (le « M » de MVC) : la structure des tables de la base."""
from .plant import Category, Plant
from .recommendation_run import RecommendationRun

__all__ = ["Category", "Plant", "RecommendationRun"]
