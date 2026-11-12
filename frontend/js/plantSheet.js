// Fiche détaillée d'une plante, affichée dans la fenêtre <dialog>.
import { el, clear } from "./dom.js";

// Champ de l'API -> libellé affiché (les valeurs restent en anglais, comme les données).
const FIELD_LABELS = [
  ["sun_requirement", "Ensoleillement"],
  ["water_requirement", "Arrosage"],
  ["soil_type", "Type de terre"],
  ["soil_ph", "pH du sol"],
  ["growing_season", "Saison"],
  ["growing_difficulty", "Difficulté"],
  ["sowing_method", "Semis"],
  ["days_to_germination", "Jours avant germination"],
  ["days_to_harvest", "Jours avant récolte"],
  ["plant_height", "Hauteur"],
  ["plant_spacing", "Espacement"],
  ["flavor_profile", "Goût"],
  ["culinary_uses", "Utilisations"],
  ["common_pests", "Ravageurs fréquents"],
  ["common_diseases", "Maladies fréquentes"],
  ["disease_resistance", "Résistance"],
];

/** Petites étiquettes résumant une plante (catégorie, soleil, saison, difficulté). */
export function plantChips(plant) {
  return el("ul", { class: "chips" },
    plant.category ? el("li", { class: "chip chip-category" }, plant.category.name) : null,
    plant.growing_difficulty ? el("li", { class: "chip" }, plant.growing_difficulty) : null,
    plant.growing_season ? el("li", { class: "chip" }, plant.growing_season) : null,
    plant.sun_requirement ? el("li", { class: "chip" }, plant.sun_requirement) : null,
    plant.is_container_friendly ? el("li", { class: "chip" }, "Culture en pot") : null
  );
}

export function openPlantSheet(plant) {
  const dialog = document.getElementById("plant-dialog");
  const content = clear(document.getElementById("plant-dialog-content"));

  const rows = FIELD_LABELS
    .filter(([field]) => plant[field])
    .map(([field, label]) => el("tr", {}, el("th", {}, label), el("td", {}, plant[field])));
  if (plant.usda_zone_min && plant.usda_zone_max) {
    rows.push(el("tr", {}, el("th", {}, "Zones de rusticité USDA"), el("td", {}, `${plant.usda_zone_min} à ${plant.usda_zone_max}`)));
  }

  content.append(
    el("h2", {}, plant.name),
    plant.scientific_name ? el("p", { class: "scientific" }, plant.scientific_name) : null,
    plantChips(plant),
    plant.description ? el("p", {}, plant.description) : null,
    el("table", { class: "data" }, el("tbody", {}, rows)),
    plant.url ? el("p", {}, el("a", { href: plant.url, target: "_blank", rel: "noopener" }, "Voir la fiche d'origine")) : null
  );
  dialog.showModal();
}
