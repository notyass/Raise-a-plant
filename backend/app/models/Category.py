from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModelMixin


class Category(Base, BaseModelMixin):
    """model de catégorie (type de plante : tomato, herb, flower...)"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)  # nom français, affiché
    name_en = Column(String(120), nullable=True)  # nom anglais du jeu de données
    plural_name = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)

    # 1-N : une catégorie possède une collection de plantes
    plants = relationship(
        'Plant',
        back_populates='category'
    )
