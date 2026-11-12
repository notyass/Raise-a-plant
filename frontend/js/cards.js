// Éléments réutilisés pour afficher une plante : étiquettes, photo, fiche cliquable.
import { el } from "./dom.js";
import { seriesColor } from "./charts.js";

/** Adresse de la page d'une plante. fromSearch : on vient d'une recherche O1. */
export function plantUrl(plant, fromSearch = false) {
  return `plante.html?id=${plant.id}` + (fromSearch ? "&recherche=1" : "");
}

/** Petites étiquettes en français résumant une plante. */
export function plantChips(plant) {
  const labels = plant.labels || {};
  return el("ul", { class: "chips" },
    plant.category ? el("li", { class: "chip chip-category" }, plant.category.name) : null,
    labels.difficulty ? el("li", { class: "chip" }, `Difficulté : ${labels.difficulty.toLowerCase()}`) : null,
    labels.sun ? el("li", { class: "chip" }, labels.sun) : null,
    labels.water ? el("li", { class: "chip" }, labels.water) : null,
    labels.season ? el("li", { class: "chip" }, labels.season) : null,
    plant.is_container_friendly ? el("li", { class: "chip" }, "Culture en pot") : null
  );
}

/** Photo de l'espèce, ou un cadre vide s'il n'y en a pas. */
export function plantPhoto(plant) {
  if (!plant.image_url) {
    return el("div", { class: "photo photo-empty", "aria-hidden": "true" }, "Pas de photo");
  }
  return el("img", { class: "photo", src: plant.image_url, loading: "lazy", alt: `Photo de ${plant.scientific_name || plant.name}` });
}

/** Crédit de la photo : auteur et licence, avec un lien vers Wikimedia Commons. */
export function photoCredit(plant) {
  if (!plant.image_url) return null;
  const text = `Photo : ${plant.image_author || "auteur inconnu"}, ${plant.image_license || "licence libre"}`;
  return el("p", { class: "photo-credit" },
    plant.image_page_url
      ? el("a", { href: plant.image_page_url, target: "_blank", rel: "noopener" }, text)
      : text,
    " (Wikimedia Commons)"
  );
}

/** Explication d'un résultat : les éléments qui ont compté, avec leur poids. */
export function whyBlock(result, explanation) {
  if (!result.matched_terms || result.matched_terms.length === 0) return null;
  return el("div", { class: "why" },
    el("div", { class: "why-title" }, "Pourquoi ce résultat ?"),
    el("p", { class: "hint" }, explanation),
    el("ul", { class: "chips" },
      result.matched_terms.map((term) => el("li", { class: "chip" }, el("b", {}, term.term), ` ${term.weight.toFixed(2)}`))
    )
  );
}

/** Fiche cliquable d'un résultat de recommandation (O2) : mène à la page de la plante. */
export function resultCard(result, approach) {
  const plant = result.plant;
  const width = Math.round(Math.min(1, Math.max(0, result.score)) * 100);
  return el("a", { class: "plant-card", href: plantUrl(plant) },
    plantPhoto(plant),
    el("div", { class: "plant-card-body" },
      el("div", { class: "result-head" },
        el("h3", {}, el("span", { class: "result-rank" }, `${result.rank}.`), plant.name),
        el("span", { class: "result-score" }, `score ${result.score.toFixed(2)}`)
      ),
      plant.scientific_name ? el("div", { class: "scientific" }, plant.scientific_name) : null,
      el("div", { class: "score-track" },
        el("div", { class: "score-fill", style: `width:${width}%;background:${seriesColor(approach.key)}` })
      ),
      plantChips(plant),
      whyBlock(result, approach.explanation)
    )
  );
}
