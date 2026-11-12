"""Tables des catégories et des plantes.

Les colonnes de Plant reprennent celles du fichier varieties.csv du jeu de
données (voir backend/data/README.md). Les textes sont en anglais.
"""
from ..extensions import db
from .mixins import SerializerMixin, TimestampMixin


class Category(db.Model, SerializerMixin):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    plural_name = db.Column(db.String(120))
    description = db.Column(db.Text)

    plants = db.relationship("Plant", back_populates="category")


class Plant(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "plants"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True
    )

    # Identité
    name = db.Column(db.Text, nullable=False, index=True)
    slug = db.Column(db.Text)
    scientific_name = db.Column(db.Text)
    description = db.Column(db.Text)

    # Culture
    days_to_harvest = db.Column(db.Text)
    days_to_germination = db.Column(db.Text)
    plant_height = db.Column(db.Text)
    plant_spacing = db.Column(db.Text)
    sun_requirement = db.Column(db.Text)
    water_requirement = db.Column(db.Text)
    soil_type = db.Column(db.Text)
    soil_ph = db.Column(db.Text)
    growing_difficulty = db.Column(db.Text)
    is_container_friendly = db.Column(db.Boolean, default=False, nullable=False)
    growing_season = db.Column(db.Text)
    sowing_method = db.Column(db.Text)

    # Description du produit récolté
    color = db.Column(db.Text)
    size = db.Column(db.Text)
    shape = db.Column(db.Text)
    flavor_profile = db.Column(db.Text)
    culinary_uses = db.Column(db.Text)
    is_heirloom = db.Column(db.Boolean, default=False, nullable=False)
    is_hybrid = db.Column(db.Boolean, default=False, nullable=False)

    # Climat, maladies, source
    usda_zone_min = db.Column(db.Integer)
    usda_zone_max = db.Column(db.Integer)
    disease_resistance = db.Column(db.Text)
    common_pests = db.Column(db.Text)
    common_diseases = db.Column(db.Text)
    source_database = db.Column(db.Text)
    url = db.Column(db.Text)

    category = db.relationship("Category", back_populates="plants")

    def to_dict(self, exclude=()):
        """Comme SerializerMixin.to_dict(), avec la catégorie en plus."""
        data = super().to_dict(exclude=exclude)
        data["category"] = (
            {"slug": self.category.slug, "name": self.category.name}
            if self.category
            else None
        )
        return data
