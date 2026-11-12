// Page d'une plante (plante.html?id=12), générée à partir de la base :
// photo, fiche et conseils d'entretien. C'est le résultat d'une recherche O1,
// et la page ouverte en cliquant sur une fiche recommandée (O2).
import "./layout.js";
import { api } from "./api.js";
import { appendAll, el, clear, formatMs } from "./dom.js";
import { seriesColor } from "./charts.js";
import { photoCredit, plantChips, plantPhoto, plantUrl, whyBlock } from "./cards.js";

const SEARCH_MEMORY = "raiseaplant:recherche"; // écrit par home.js après une recherche O1
const params = new URLSearchParams(window.location.search);
const plantId = Number.parseInt(params.get("id"), 10);

// Champs affichés tels quels (en anglais, comme dans le jeu de données).
const OTHER_FIELDS = [
  ["soil_ph", "pH du sol"],
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

/** Rappel de la recherche O1 : méthode, temps, explication et autres résultats. */
function renderSearchSummary() {
  if (params.get("recherche") !== "1") return;
  let search = null;
  try { search = JSON.parse(sessionStorage.getItem(SEARCH_MEMORY)); } catch (error) { /* mémoire indisponible */ }
  if (!search) return;
  const current = search.results.find((result) => result.plant.id === plantId);
  if (!current) return;

  const others = search.results.filter((result) => result.plant.id !== plantId);
  const summary = document.getElementById("search-summary");
  appendAll(summary,
    el("p", {},
      "Recherche ", el("strong", {}, `« ${search.query_text} »`), " · ",
      el("span", { class: "swatch", style: `background:${seriesColor(search.approach.key)}` }),
      search.approach.label, ` · ${search.count} résultat(s) · calcul en ${formatMs(search.timing.algo_ms)}`
    ),
    whyBlock(current, search.approach.explanation),
    others.length > 0
      ? el("div", {},
          el("p", { class: "hint" }, "Autres résultats de cette recherche :"),
          el("ul", { class: "chips" }, others.map((result) =>
            el("li", {}, el("a", { class: "chip chip-link", href: plantUrl(result.plant, true) },
              `${result.rank}. ${result.plant.name}`))))
        )
      : null
  );
  summary.hidden = false;
}

function careCard(item) {
  return el("section", { class: "care-card" },
    el("h3", {}, item.title),
    item.advice.map((sentence) => el("p", {}, sentence)),
    // texte d'origine du jeu de données : plus précis, mais en anglais
    item.detail ? el("p", { class: "original" }, `Fiche d'origine : ${item.detail}`) : null
  );
}

function renderPlant(plant) {
  document.title = `Raise a Plant — ${plant.name}`;
  const rows = OTHER_FIELDS
    .filter(([field]) => plant[field])
    .map(([field, title]) => el("tr", {}, el("th", {}, title), el("td", {}, plant[field])));
  if (plant.usda_zone_min && plant.usda_zone_max) {
    rows.push(el("tr", {}, el("th", {}, "Zones de rusticité USDA"), el("td", {}, `${plant.usda_zone_min} à ${plant.usda_zone_max}`)));
  }

  appendAll(clear(document.getElementById("plant-page")),
    el("div", { class: "plant-hero panel" },
      el("div", { class: "plant-hero-photo" }, plantPhoto(plant), photoCredit(plant)),
      el("div", {},
        el("h2", {}, plant.name),
        plant.scientific_name ? el("p", { class: "scientific" }, plant.scientific_name) : null,
        plantChips(plant),
        plant.description ? el("p", {}, plant.description) : null,
        plant.description ? el("p", { class: "original" }, "Description d'origine, en anglais.") : null
      )
    ),
    el("h2", {}, "Comment en prendre soin"),
    plant.care.length > 0
      ? el("div", { class: "care-grid" }, plant.care.map(careCard))
      : el("p", { class: "placeholder" }, "La fiche de cette plante ne contient pas de consigne d'entretien."),
    rows.length > 0 ? el("h2", {}, "Autres informations") : null,
    rows.length > 0 ? el("div", { class: "panel" }, el("table", { class: "data" }, el("tbody", {}, rows))) : null,
    plant.url ? el("p", {}, el("a", { href: plant.url, target: "_blank", rel: "noopener" }, "Voir la fiche d'origine")) : null
  );
}

async function start() {
  const page = document.getElementById("plant-page");
  if (!Number.isInteger(plantId)) {
    clear(page).append(el("p", { class: "placeholder" }, "Aucune plante demandée. Reviens à l'accueil pour faire une recherche."));
    return;
  }
  try {
    renderSearchSummary();
    renderPlant(await api.plant(plantId));
  } catch (error) {
    clear(page).append(el("p", { class: "error" }, error.message));
  }
}

start();
