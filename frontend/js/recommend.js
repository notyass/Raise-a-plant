// Vue « Recommander » : formulaire, résultats et mini tableau de bord de la requête.
import { api } from "./api.js";
import { el, clear, formatMs, formatNumber, tile } from "./dom.js";
import { chartBox, drawScoreChart, seriesColor } from "./charts.js";
import { openPlantSheet, plantChips } from "./plantSheet.js";

const form = document.getElementById("recommend-form");
const output = document.getElementById("recommend-output");
const errorBox = document.getElementById("recommend-error");
const statusBox = document.getElementById("recommend-status");
let scoreChart = null;

/** Remplit le formulaire à partir de l'API (critères, catégories, approches). */
export async function initRecommend() {
  const [options, categories, approaches] = await Promise.all([
    api.options(), api.categories(), api.approaches(),
  ]);

  // Un menu déroulant par critère (soleil, eau, terre, saison, niveau).
  const criteriaFields = clear(document.getElementById("criteria-fields"));
  for (const [key, criterion] of Object.entries(options)) {
    criteriaFields.append(
      el("label", { class: "field" },
        el("span", {}, criterion.label),
        el("select", { name: key },
          el("option", { value: "" }, "Peu importe"),
          criterion.choices.map((choice) => el("option", { value: choice.value }, choice.label))
        )
      )
    );
  }

  const categorySelect = document.getElementById("field-category");
  for (const category of categories.items) {
    if (category.plant_count > 0) {
      categorySelect.append(el("option", { value: category.slug }, `${category.name} (${category.plant_count})`));
    }
  }

  const approachSelect = clear(document.getElementById("field-approach"));
  for (const approach of approaches.items) {
    approachSelect.append(
      el("option", { value: approach.key, disabled: !approach.available },
        approach.available ? approach.label : `${approach.label} (indisponible)`)
    );
  }
  // Si une approche manque, on dit pourquoi sous le menu.
  const missing = approaches.items.filter((approach) => !approach.available);
  const note = document.getElementById("approach-note");
  note.textContent = missing.map((approach) => `${approach.label} : ${approach.unavailable_reason}`).join(" ");
  note.hidden = missing.length === 0;

  form.addEventListener("submit", onSubmit);
  form.addEventListener("reset", () => { errorBox.hidden = true; });
}

/** Lit le formulaire et renvoie le corps de la requête pour l'API. */
function readForm() {
  const data = new FormData(form);
  const criteria = {};
  for (const [key, value] of data.entries()) {
    if (["approach", "top_k", "container"].includes(key)) continue;
    if (typeof value === "string" && value.trim() !== "") criteria[key] = value.trim();
  }
  if (data.get("container")) criteria.container = true;
  return {
    criteria,
    approach: data.get("approach") || "tfidf",
    top_k: Number.parseInt(data.get("top_k"), 10) || 10,
  };
}

async function onSubmit(event) {
  event.preventDefault();
  errorBox.hidden = true;
  const submitButton = form.querySelector("button[type=submit]");
  submitButton.disabled = true;
  const body = readForm();
  statusBox.textContent = body.approach === "embeddings"
    ? "Calcul en cours… La toute première utilisation de cette approche peut prendre une à deux minutes (chargement du modèle et calcul des vecteurs)."
    : "Calcul en cours…";
  statusBox.hidden = false;
  try {
    const result = await api.recommend(body);
    // Les moyennes de l'approche servent à situer cette requête.
    const metrics = await api.metrics().catch(() => null);
    renderResult(result, metrics);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    submitButton.disabled = false;
    statusBox.hidden = true;
  }
}

function renderResult(result, metrics) {
  if (scoreChart) { scoreChart.destroy(); scoreChart = null; }
  clear(output);

  const approachMetrics = metrics
    ? metrics.approaches.find((approach) => approach.key === result.approach.key)
    : null;
  const mean = approachMetrics ? approachMetrics.algo_ms.mean : null;
  const count = approachMetrics ? approachMetrics.algo_ms.count : 0;

  output.append(
    el("div", { class: "summary" },
      el("h2", {}, result.count > 0 ? `${result.count} plante(s) recommandée(s)` : "Aucune plante trouvée"),
      el("p", { class: "hint" },
        "Approche : ", el("span", { class: "swatch", style: `background:${seriesColor(result.approach.key)}` }),
        el("strong", {}, result.approach.label),
        " · requête envoyée à l'algorithme : ", el("span", { class: "query-text" }, result.query_text)
      )
    ),
    // Mini tableau de bord de cette recommandation
    el("div", { class: "tiles" },
      tile("Temps de calcul", formatMs(result.timing.algo_ms), "algorithme seul"),
      tile("Temps serveur total", formatMs(result.timing.total_ms), "calcul + base de données"),
      tile("Moyenne de l'approche", formatMs(mean), count ? `sur ${formatNumber(count)} recommandation(s)` : null),
      tile("Fiches comparées", formatNumber(result.corpus_size), "taille du corpus")
    )
  );

  if (result.count === 0) {
    output.append(el("p", { class: "placeholder" },
      "Aucune fiche ne correspond à ta demande. Essaie avec moins de critères ou d'autres mots-clés."));
    return;
  }

  const { box, canvas } = chartBox(
    "Score de similarité des plantes recommandées",
    "Plus la barre est longue, plus la fiche ressemble à ta demande.",
    Math.max(140, 28 * result.count + 60)
  );
  output.append(box);
  scoreChart = drawScoreChart(canvas, result.results, result.approach.key);

  const bestScore = result.results[0].score;
  for (const item of result.results) {
    output.append(resultCard(item, bestScore, result.approach));
  }
}

function resultCard(item, bestScore, approach) {
  const plant = item.plant;
  // Longueur de la barre : proportionnelle au meilleur score, bornée entre 0 et 100 %.
  const ratio = bestScore > 0 ? Math.min(1, Math.max(0, item.score / bestScore)) : 0;
  return el("article", { class: "result-card" },
    el("div", { class: "result-head" },
      el("h3", {}, el("span", { class: "result-rank" }, `${item.rank}.`), plant.name),
      el("span", { class: "result-score" }, `score ${item.score.toFixed(3)}`)
    ),
    plant.scientific_name ? el("div", { class: "scientific" }, plant.scientific_name) : null,
    // Barre proportionnelle au meilleur score de la liste
    el("div", { class: "score-track" },
      el("div", { class: "score-fill", style: `width:${Math.round(ratio * 100)}%;background:${seriesColor(approach.key)}` })
    ),
    plantChips(plant),
    plant.description ? el("p", { class: "description" }, plant.description) : null,
    el("button", { type: "button", class: "button-link", onclick: () => openPlantSheet(plant) }, "Voir la fiche complète"),
    // Explication : pourquoi cette plante ? Le texte dépend de l'approche.
    item.matched_terms.length > 0
      ? el("div", { class: "why" },
          el("div", { class: "why-title" }, "Pourquoi cette plante ?"),
          el("p", { class: "hint" }, approach.explanation),
          el("ul", { class: "chips" },
            item.matched_terms.map((term) => el("li", { class: "chip" }, el("b", {}, term.term), ` ${term.weight.toFixed(3)}`))
          )
        )
      : null
  );
}
