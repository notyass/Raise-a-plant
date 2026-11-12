// Tableau de bord : une carte par méthode, côte à côte, avec les mêmes
// mesures pour chacun des deux objectifs, afin de pouvoir les comparer.
import "./layout.js";
import { api } from "./api.js";
import { el, clear, formatMs, formatNumber, tile } from "./dom.js";
import { chartBox, drawHistoryChart, seriesColor } from "./charts.js";

const content = document.getElementById("dashboard-content");
let charts = [];

async function loadDashboard() {
  charts.forEach((chart) => chart && chart.destroy());
  charts = [];
  clear(content);
  try {
    const metrics = await api.metrics();
    for (const approach of metrics.approaches) {
      content.append(approachCard(approach, metrics.objectives));
    }
  } catch (error) {
    content.append(el("p", { class: "error" }, error.message));
  }
}

function approachCard(approach, objectives) {
  const card = el("section", { class: "panel approach-card" },
    el("h3", {}, el("span", { class: "swatch", style: `background:${seriesColor(approach.key)}` }), approach.label),
    el("p", {}, approach.description)
  );
  for (const [key, label] of Object.entries(objectives)) {
    card.append(objectiveBlock(approach, key, label));
  }
  card.append(el("h4", {}, "Index en mémoire"), indexTable(approach.index));
  card.append(el("h4", {}, "Complexité algorithmique"), complexityTable(approach.complexity));
  return card;
}

/** Mesures d'une méthode pour un objectif (O1 ou O2). */
function objectiveBlock(approach, objectiveKey, objectiveLabel) {
  const measured = approach.objectives[objectiveKey];
  const algo = measured.algo_ms;
  const block = el("div", { class: "objective-block" }, el("h4", {}, objectiveLabel));

  if (algo.count === 0) {
    block.append(el("p", { class: "hint" }, "Aucune mesure pour l'instant : fais une recherche depuis la page d'accueil de cette méthode."));
    return block;
  }

  block.append(
    el("div", { class: "tiles" },
      tile("Recherches", formatNumber(algo.count)),
      tile("Minimum", formatMs(algo.min)),
      tile("Moyenne", formatMs(algo.mean)),
      tile("Médiane", formatMs(algo.median)),
      tile("95e centile", formatMs(algo.p95)),
      tile("Maximum", formatMs(algo.max)),
      tile("Sans résultat", formatNumber(measured.empty_count), "recherches restées vides")
    )
  );

  const { box, canvas } = chartBox(
    "Temps de calcul des dernières recherches",
    `${approach.label} · ${measured.history.length} dernière(s) mesure(s), en millisecondes`,
    180
  );
  block.append(box);
  charts.push(drawHistoryChart(canvas, measured.history, approach.key));

  block.append(
    el("details", {},
      el("summary", {}, "Voir les mesures en tableau"),
      el("table", { class: "data" },
        el("thead", {}, el("tr", {},
          el("th", {}, "Recherche n°"), el("th", { class: "num" }, "Calcul"),
          el("th", { class: "num" }, "Total serveur"), el("th", { class: "num" }, "Résultats"))),
        el("tbody", {}, measured.history.map((point) => el("tr", {},
          el("td", {}, point.run_id), el("td", { class: "num" }, formatMs(point.algo_ms)),
          el("td", { class: "num" }, formatMs(point.total_ms)), el("td", { class: "num" }, point.result_count))))
      )
    ),
    el("p", { class: "hint" },
      `Temps serveur total (calcul + base de données) : moyenne ${formatMs(measured.total_ms.mean)}, maximum ${formatMs(measured.total_ms.max)}.`)
  );
  return block;
}

function row(label, value) {
  return el("tr", {}, el("th", {}, label), el("td", {}, value));
}

// Mesures possibles d'un index : clé renvoyée par l'API -> libellé et mise en forme.
// Chaque méthode ne renvoie que les mesures qui la concernent.
const INDEX_ROWS = [
  ["documents", "Fiches indexées (N)", formatNumber],
  ["weighted_criteria", "Critères du barème", formatNumber],
  ["dimensions", "Coordonnées par fiche (d)", formatNumber],
  ["letter_pairs", "Paires de lettres différentes", formatNumber],
  ["matrix_memory_kb", "Mémoire des matrices", (value) => `${formatNumber(value)} Ko`],
  ["fit_duration_ms", "Temps de construction", formatMs],
];

function indexTable(index) {
  if (!index) {
    return el("p", { class: "hint" }, "L'index est construit à la première recherche : ses mesures apparaîtront ensuite.");
  }
  return el("table", { class: "data" }, el("tbody", {},
    INDEX_ROWS
      .filter(([key]) => index[key] !== undefined && index[key] !== null)
      .map(([key, label, format]) => row(label, format(index[key])))
  ));
}

function complexityTable(complexity) {
  return el("table", { class: "data" }, el("tbody", {},
    row("Construction de l'index", complexity.indexation),
    row("O1 : retrouver une plante", complexity.recherche),
    row("O2 : recommander", complexity.recommandation),
    row("Mémoire", complexity.memoire),
    row("Notations", complexity.notation),
    row("Pistes d'optimisation", complexity.pistes)
  ));
}

document.getElementById("dashboard-refresh").addEventListener("click", loadDashboard);
loadDashboard();
