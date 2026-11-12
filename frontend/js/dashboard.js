// Vue « Tableau de bord » : une carte par approche de recommandation,
// côte à côte, avec les mêmes mesures pour pouvoir les comparer.
import { api } from "./api.js";
import { el, clear, formatMs, formatNumber, tile } from "./dom.js";
import { chartBox, drawHistoryChart, seriesColor } from "./charts.js";

const content = document.getElementById("dashboard-content");
let charts = [];

export function initDashboard() {
  document.getElementById("dashboard-refresh").addEventListener("click", loadDashboard);
}

export async function loadDashboard() {
  charts.forEach((chart) => chart && chart.destroy());
  charts = [];
  clear(content);
  try {
    const metrics = await api.metrics();
    for (const approach of metrics.approaches) {
      content.append(approach.available ? approachCard(approach) : unavailableCard(approach));
    }
  } catch (error) {
    content.append(el("p", { class: "error" }, error.message));
  }
}

function unavailableCard(approach) {
  return el("section", { class: "panel approach-card is-planned" },
    el("h3", {}, el("span", { class: "swatch", style: `background:${seriesColor(approach.key)}` }), approach.label),
    el("p", {}, approach.description),
    el("p", { class: "hint" }, `Approche indisponible sur ce serveur. ${approach.unavailable_reason || ""}`)
  );
}

function approachCard(approach) {
  const algo = approach.algo_ms;
  const total = approach.total_ms;
  const card = el("section", { class: "panel approach-card" },
    el("h3", {}, el("span", { class: "swatch", style: `background:${seriesColor(approach.key)}` }), approach.label),
    el("p", {}, approach.description)
  );

  if (algo.count === 0) {
    card.append(el("p", { class: "placeholder" }, "Aucune mesure pour l'instant : lance une recommandation dans l'onglet « Recommander »."));
  } else {
    card.append(
      el("h4", {}, "Temps de calcul de l'algorithme"),
      el("div", { class: "tiles" },
        tile("Mesures", formatNumber(algo.count)),
        tile("Minimum", formatMs(algo.min)),
        tile("Moyenne", formatMs(algo.mean)),
        tile("Médiane", formatMs(algo.median)),
        tile("95e centile", formatMs(algo.p95), "95 % des requêtes sont plus rapides"),
        tile("Maximum", formatMs(algo.max))
      )
    );

    const { box, canvas } = chartBox(
      "Temps de calcul des dernières recommandations",
      `${approach.label} · ${approach.history.length} dernière(s) mesure(s), en millisecondes`
    );
    card.append(box);
    charts.push(drawHistoryChart(canvas, approach.history, approach.key));

    card.append(
      el("details", {},
        el("summary", {}, "Voir les mesures en tableau"),
        el("table", { class: "data" },
          el("thead", {}, el("tr", {},
            el("th", {}, "Recommandation n°"), el("th", { class: "num" }, "Calcul"),
            el("th", { class: "num" }, "Total serveur"), el("th", { class: "num" }, "Résultats"))),
          el("tbody", {}, approach.history.map((point) => el("tr", {},
            el("td", {}, point.run_id), el("td", { class: "num" }, formatMs(point.algo_ms)),
            el("td", { class: "num" }, formatMs(point.total_ms)), el("td", { class: "num" }, point.result_count))))
        )
      ),
      el("h4", {}, "Temps serveur total (calcul + base de données)"),
      el("div", { class: "tiles" },
        tile("Minimum", formatMs(total.min)),
        tile("Moyenne", formatMs(total.mean)),
        tile("Maximum", formatMs(total.max))
      )
    );
  }

  card.append(el("h4", {}, "Index en mémoire"), indexTable(approach.index));
  card.append(el("h4", {}, "Complexité algorithmique"), complexityTable(approach.complexity));
  return card;
}

function row(label, value) {
  return el("tr", {}, el("th", {}, label), el("td", {}, value));
}

// Mesures possibles d'un index : clé renvoyée par l'API -> libellé et mise en forme.
// Chaque approche ne renvoie que les mesures qui la concernent.
const INDEX_ROWS = [
  ["model_name", "Modèle de langage", (value) => value],
  ["documents", "Fiches indexées (N)", formatNumber],
  ["vocabulary_size", "Taille du vocabulaire (V)", formatNumber],
  ["avg_terms_per_document", "Termes distincts par fiche (L)", formatNumber],
  ["non_zero_values", "Valeurs non nulles de la matrice", formatNumber],
  ["dimensions", "Dimension des vecteurs (d)", formatNumber],
  ["matrix_memory_kb", "Mémoire de la matrice", (value) => `${formatNumber(value)} Ko`],
  ["fit_duration_ms", "Temps de construction", formatMs],
  ["loaded_from_cache", "Vecteurs relus depuis le disque", (value) => (value ? "Oui" : "Non, calculés à ce démarrage")],
  ["model_load_ms", "Chargement du modèle", formatMs],
];

function indexTable(index) {
  if (!index) {
    return el("p", { class: "hint" }, "L'index est construit à la première recommandation : ses mesures apparaîtront ensuite.");
  }
  return el("table", { class: "data" }, el("tbody", {},
    INDEX_ROWS
      .filter(([key]) => index[key] !== undefined && index[key] !== null)
      .map(([key, label, format]) => row(label, format(index[key])))
  ));
}

function complexityTable(complexity) {
  if (!complexity) return el("p", { class: "hint" }, "Non renseignée.");
  return el("table", { class: "data" }, el("tbody", {},
    row("Construction de l'index", complexity.indexation),
    row("Une recommandation", complexity.requete),
    row("Mémoire", complexity.memoire),
    row("Notations", complexity.notation),
    row("Pistes d'optimisation", complexity.pistes)
  ));
}
