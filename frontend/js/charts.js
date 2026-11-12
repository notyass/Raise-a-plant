// Graphiques Chart.js. Règles suivies :
//  - une couleur par approche, toujours la même (TF-IDF = bleu, embeddings = orange) ;
//  - les textes restent en gris/noir, seules les marques portent la couleur ;
//  - traits fins, grille discrète, info-bulle au survol.
import { el } from "./dom.js";

export const SERIES_COLORS = { tfidf: "#2a78d6", embeddings: "#eb6834" };
const TEXT_SECONDARY = "#52514e";
const GRID = "#e6e7e1";

export function seriesColor(approachKey) {
  return SERIES_COLORS[approachKey] || "#7a7972";
}

/** Vrai si Chart.js a bien été chargé depuis le CDN. */
export function chartsAvailable() {
  return typeof window.Chart !== "undefined";
}

/** Crée le cadre d'un graphique (titre, sous-titre, zone de dessin). */
export function chartBox(title, subtitle, height = 220) {
  const canvas = el("canvas", { role: "img", "aria-label": title });
  const box = el("div", { class: "chart-box" },
    el("div", { class: "chart-title" }, title),
    subtitle ? el("div", { class: "chart-subtitle" }, subtitle) : null,
    chartsAvailable()
      ? el("div", { class: "chart-canvas", style: `height:${height}px` }, canvas)
      : el("p", { class: "hint" }, "Graphique indisponible : Chart.js n'a pas pu être chargé (connexion internet nécessaire).")
  );
  return { box, canvas };
}

function baseOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false }, // une seule série : le titre dit ce qui est tracé
      tooltip: { displayColors: false },
    },
  };
}

function axis(title, extra = {}) {
  return {
    title: { display: Boolean(title), text: title, color: TEXT_SECONDARY },
    ticks: { color: TEXT_SECONDARY },
    grid: { color: GRID },
    border: { display: false },
    ...extra,
  };
}

/** Barres horizontales : score de similarité de chaque plante recommandée. */
export function drawScoreChart(canvas, results, approachKey) {
  if (!chartsAvailable()) return null;
  const shorten = (name) => (name.length > 26 ? name.slice(0, 25) + "…" : name);
  const options = baseOptions();
  options.indexAxis = "y";
  options.scales = {
    x: axis("Score de similarité (cosinus)", { beginAtZero: true }),
    y: axis("", { grid: { display: false } }),
  };
  options.plugins.tooltip.callbacks = {
    title: (items) => results[items[0].dataIndex].plant.name,
    label: (item) => `Score : ${item.parsed.x.toFixed(3)}`,
  };
  return new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: results.map((result) => `${result.rank}. ${shorten(result.plant.name)}`),
      datasets: [{
        data: results.map((result) => result.score),
        backgroundColor: seriesColor(approachKey),
        borderRadius: 4,       // extrémité arrondie côté valeur
        borderSkipped: "start", // base carrée
        maxBarThickness: 16,
      }],
    },
    options,
  });
}

/** Courbe : temps de calcul des dernières recommandations d'une approche. */
export function drawHistoryChart(canvas, history, approachKey) {
  if (!chartsAvailable()) return null;
  const color = seriesColor(approachKey);
  const options = baseOptions();
  options.interaction = { mode: "index", intersect: false };
  options.scales = {
    x: axis("Recommandation n°", { grid: { display: false }, ticks: { color: TEXT_SECONDARY, maxTicksLimit: 10 } }),
    y: axis("Temps de calcul (ms)", { beginAtZero: true }),
  };
  options.plugins.tooltip.callbacks = {
    title: (items) => `Recommandation n° ${items[0].label}`,
    label: (item) => `Calcul : ${item.parsed.y.toFixed(2)} ms`,
  };
  return new window.Chart(canvas, {
    type: "line",
    data: {
      labels: history.map((point) => point.run_id),
      datasets: [{
        data: history.map((point) => point.algo_ms),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        tension: 0,
        pointRadius: history.length <= 1 ? 4 : 0, // un seul point : on le montre
        pointHoverRadius: 5,
        pointHoverBorderWidth: 2,
        pointHoverBorderColor: "#fcfcfb",
      }],
    },
    options,
  });
}
