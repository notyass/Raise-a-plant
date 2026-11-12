// Vue « Catalogue » : parcourir toutes les plantes, avec filtre et pagination.
import { api } from "./api.js";
import { el, clear, formatNumber } from "./dom.js";
import { openPlantSheet, plantChips } from "./plantSheet.js";

const grid = document.getElementById("catalogue-grid");
const pagination = document.getElementById("catalogue-pagination");
const countLabel = document.getElementById("catalogue-count");
const filters = document.getElementById("catalogue-filters");
const PER_PAGE = 24;
let loaded = false;

export async function initCatalogue() {
  const categories = await api.categories();
  const select = document.getElementById("catalogue-category");
  for (const category of categories.items) {
    if (category.plant_count > 0) {
      select.append(el("option", { value: category.slug }, `${category.name} (${category.plant_count})`));
    }
  }
  filters.addEventListener("submit", (event) => { event.preventDefault(); loadPage(1); });
  select.addEventListener("change", () => loadPage(1));
}

/** Charge la première page la première fois qu'on ouvre l'onglet. */
export function showCatalogue() {
  if (!loaded) loadPage(1);
}

async function loadPage(page) {
  const data = new FormData(filters);
  const params = { page, per_page: PER_PAGE };
  if (data.get("category")) params.category = data.get("category");
  if (data.get("q").trim()) params.q = data.get("q").trim();

  clear(grid);
  clear(pagination);
  try {
    const result = await api.plants(params);
    loaded = true;
    countLabel.textContent = `${formatNumber(result.total)} plante(s)`;
    if (result.items.length === 0) {
      grid.append(el("p", { class: "placeholder" }, "Aucune plante ne correspond."));
      return;
    }
    for (const plant of result.items) {
      grid.append(
        el("button", { type: "button", class: "plant-card", onclick: () => openPlantSheet(plant) },
          el("h3", {}, plant.name),
          plant.scientific_name ? el("div", { class: "scientific" }, plant.scientific_name) : null,
          plantChips(plant)
        )
      );
    }
    pagination.append(
      el("button", { type: "button", class: "button", disabled: result.page <= 1, onclick: () => loadPage(result.page - 1) }, "Précédent"),
      el("span", {}, `Page ${result.page} sur ${result.pages}`),
      el("button", { type: "button", class: "button", disabled: result.page >= result.pages, onclick: () => loadPage(result.page + 1) }, "Suivant")
    );
  } catch (error) {
    grid.append(el("p", { class: "error" }, error.message));
  }
}
