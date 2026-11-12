from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModelMixin, TimestampMixin


class Plant(Base, BaseModelMixin, TimestampMixin):
    """model de plante
    Les colonnes reprennent celles du fichier varieties.csv du jeu de données
    (voir backend/data/README.md). Les textes sont en anglais ; les colonnes
    *_codes en sont la version normalisée, affichée en français.
    relation : category N-1
    """
    __tablename__ = 'plants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False, index=True)

    # identité
    name = Column(Text, nullable=False, index=True)
    slug = Column(Text, nullable=True)
    scientific_name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # culture
    days_to_harvest = Column(Text, nullable=True)
    days_to_germination = Column(Text, nullable=True)
    plant_height = Column(Text, nullable=True)
    plant_spacing = Column(Text, nullable=True)
    sun_requirement = Column(Text, nullable=True)
    water_requirement = Column(Text, nullable=True)
    soil_type = Column(Text, nullable=True)
    soil_ph = Column(Text, nullable=True)
    growing_difficulty = Column(Text, nullable=True)
    is_container_friendly = Column(Boolean, default=False, nullable=False)
    growing_season = Column(Text, nullable=True)
    sowing_method = Column(Text, nullable=True)

    # caractéristiques normalisées à l'import (voir services/normalizer.py) :
    # codes séparés par des virgules, ex. "full_sun,partial_shade"
    sun_codes = Column(Text, nullable=True)
    water_codes = Column(Text, nullable=True)
    soil_codes = Column(Text, nullable=True)
    season_codes = Column(Text, nullable=True)
    difficulty_codes = Column(Text, nullable=True)

    # description du produit récolté
    color = Column(Text, nullable=True)
    size = Column(Text, nullable=True)
    shape = Column(Text, nullable=True)
    flavor_profile = Column(Text, nullable=True)
    culinary_uses = Column(Text, nullable=True)
    is_heirloom = Column(Boolean, default=False, nullable=False)
    is_hybrid = Column(Boolean, default=False, nullable=False)

    # climat, maladies, source
    usda_zone_min = Column(Integer, nullable=True)
    usda_zone_max = Column(Integer, nullable=True)
    disease_resistance = Column(Text, nullable=True)
    common_pests = Column(Text, nullable=True)
    common_diseases = Column(Text, nullable=True)
    source_database = Column(Text, nullable=True)
    url = Column(Text, nullable=True)

    # photo de l'espèce (Wikimedia Commons), remplie par prepa_images.py
    image_url = Column(Text, nullable=True)
    image_author = Column(Text, nullable=True)
    image_license = Column(Text, nullable=True)
    image_page_url = Column(Text, nullable=True)

    #### relations

    category = relationship(
        'Category',
        back_populates='plants'
    )

    def to_dict(self):
        """comme BaseModelMixin.to_dict(), avec la catégorie en plus"""
        result = super().to_dict()
        result['category'] = (
            {'slug': self.category.slug, 'name': self.category.name}
            if self.category
            else None
        )
        return result
