// Page d'accueil. Il y en a deux, identiques sauf la méthode utilisée :
// index.html (heuristique) et vectorielle.html (vectorielle). La méthode est
// lue dans <body data-approach="...">.
import "./layout.js";
import { api } from "./api.js";
import { el, clear, formatMs, formatNumber, tile } from "./dom.js";
import { chartBox, drawScoreChart, seriesColor } from "./charts.js";
import { plantUrl, resultCard } from "./cards.js";

const APPROACH_KEY = document.body.dataset.approach;
const TWIN_PAGE = document.body.dataset.twin;
const SEARCH_RESULTS = 8; // nombre de fiches demandées pour une recherche O1
const RECOMMENDATIONS = 12; // nombre de fiches demandées pour une recherche O2
// Mémoire de l'onglet : garde la dernière demande pour la refaire sur l'autre page.
const FORM_MEMORY = "raiseaplant:demande";
const SEARCH_MEMORY = "raiseaplant:recherche";

const careForm = document.getElementById("care-form");
const environmentForm = document.getElementById("environment-form");
const results = document.getElementById("results");
let approach = null; // description de la méthode de cette page
let options = {}; // critères du formulaire O2
let scoreChart = null;

function remember(key, value) {
  try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (error) { /* mémoire indisponible */ }
}

function recall(key) {
  try { return JSON.parse(sessionStorage.getItem(key)); } catch (error) { return null; }
}

function showError(id, message) {
  const box = document.getElementById(id);
  box.textContent = message || "";
  box.hidden = !message;
}

// ----- Mise en place de la page -----

function buildMethodBanner(approaches) {
  const other = approaches.find((item) => item.key !== APPROACH_KEY);
  clear(document.getElementById("method-banner")).append(
    el("p", { class: "method-name" },
      el("span", { class: "swatch", style: `background:${seriesColor(APPROACH_KEY)}` }),
      "Cette page utilise la méthode ", el("strong", {}, approach.label)
    ),
    el("p", {}, approach.description),
    el("p", {}, el("a", { href: TWIN_PAGE }, `Faire les mêmes recherches avec la méthode ${other.label} →`))
  );
}

/** Niveau désigné par un curseur : même découpage en parts égales que le backend. */
function sliderLevel(criterion, percent) {
  const index = Math.min(criterion.choices.length - 1, Math.floor((percent / 100) * criterion.choices.length));
  return criterion.choices[index];
}

function buildCriteriaFields() {
  const container = clear(document.getElementById("criteria-fields"));
  for (const [key, criterion] of Object.entries(options)) {
    if (criterion.type === "slider") {
      const first = criterion.choices[0];
      const last = criterion.choices[criterion.choices.length - 1];
      const output = el("output", { class: "slider-value" });
      const range = el("input", { type: "range", name: key, min: "0", max: "100", step: "5", value: "50", "aria-label": criterion.label });
      const toggle = el("input", { type: "checkbox", name: `use_${key}`, checked: true });
      const refresh = () => {
        range.disabled = !toggle.checked;
        output.textContent = toggle.checked
          ? `${sliderLevel(criterion, Number(range.value)).label} (${range.value} %)`
          : "Peu importe";
      };
      range.addEventListener("input", refresh);
      toggle.addEventListener("change", refresh);
      container.append(
        el("div", { class: "slider-row" },
          el("div", { class: "slider-head" },
            el("label", { class: "slider-toggle" }, toggle, el("span", {}, criterion.label)),
            output
          ),
          range,
          el("div", { class: "slider-ends" }, el("span", {}, first.label), el("span", {}, last.label))
        )
      );
      refresh();
    } else {
      container.append(
        el("label", { class: "field" },
          el("span", {}, criterion.label),
          el("select", { name: key },
            el("option", { value: "" }, "Peu importe"),
            criterion.choices.map((choice) => el("option", { value: choice.value }, choice.label))
          )
        )
      );
    }
  }
}

/** Remet dans les formulaires la dernière demande faite dans cet onglet. */
function restoreForms() {
  const memory = recall(FORM_MEMORY);
  if (!memory) return;
  if (memory.query) careForm.elements.query.value = memory.query;
  for (const [key, criterion] of Object.entries(options)) {
    const value = memory.criteria ? memory.criteria[key] : undefined;
    if (criterion.type === "slider") {
      environmentForm.elements[`use_${key}`].checked = value !== undefined;
      if (value !== undefined) environmentForm.elements[key].value = value;
    } else if (value !== undefined) {
      environmentForm.elements[key].value = value;
    }
  }
  if (memory.criteria) {
    environmentForm.elements.category.value = memory.criteria.category || "";
    environmentForm.elements.container.checked = Boolean(memory.criteria.container);
  }
  environmentForm.querySelectorAll("input[type=range], input[name^=use_]").forEach((input) => {
    input.dispatchEvent(new Event(input.type === "range" ? "input" : "change"));
  });
}

// ----- O1 : prendre soin d'une plante -----

async function onCareSubmit(event) {
  event.preventDefault();
  showError("care-error", null);
  const query = careForm.elements.query.value.trim();
  if (!query) {
    showError("care-error", "Écris le nom d'une plante.");
    return;
  }
  remember(FORM_MEMORY, { ...(recall(FORM_MEMORY) || {}), query });
  try {
    const result = await api.search(query, APPROACH_KEY, SEARCH_RESULTS);
    if (result.count === 0) {
      showError("care-error",
        `Aucune plante trouvée pour « ${query} » avec la méthode ${approach.label}. ` +
        (APPROACH_KEY === "heuristic"
          ? "Ses règles demandent les bonnes lettres, sans faute de frappe : vérifie l'orthographe ou essaie la méthode vectorielle."
          : "Essaie un autre nom."));
      return;
    }
    // La recherche affiche directement la page de la meilleure plante ;
    // les autres résultats y sont proposés.
    remember(SEARCH_MEMORY, result);
    window.location.href = plantUrl(result.results[0].plant, true);
  } catch (error) {
    showError("care-error", error.message);
  }
}

// ----- O2 : des plantes pour mon environnement -----

function readCriteria() {
  const criteria = {};
  for (const [key, criterion] of Object.entries(options)) {
    if (criterion.type === "slider") {
      if (environmentForm.elements[`use_${key}`].checked) criteria[key] = Number(environmentForm.elements[key].value);
    } else if (environmentForm.elements[key].value) {
      criteria[key] = environmentForm.elements[key].value;
    }
  }
  if (environmentForm.elements.category.value) criteria.category = environmentForm.elements.category.value;
  if (environmentForm.elements.container.checked) criteria.container = true;
  return criteria;
}

async function onEnvironmentSubmit(event) {
  event.preventDefault();
  showError("environment-error", null);
  const criteria = readCriteria();
  remember(FORM_MEMORY, { ...(recall(FORM_MEMORY) || {}), criteria });
  const button = environmentForm.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const result = await api.recommend(criteria, APPROACH_KEY, RECOMMENDATIONS);
    const metrics = await api.metrics().catch(() => null); // pour situer cette recherche
    renderRecommendation(result, metrics);
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError("environment-error", error.message);
  } finally {
    button.disabled = false;
  }
}

function renderRecommendation(result, metrics) {
  if (scoreChart) { scoreChart.destroy(); scoreChart = null; }
  clear(results);

  const measured = metrics
    ? metrics.approaches.find((item) => item.key === result.approach.key).objectives.environment
    : null;

  results.append(
    el("div", { class: "summary" },
      el("h2", {}, result.count > 0 ? `${result.count} plante(s) pour ton environnement` : "Aucune plante trouvée"),
      el("p", { class: "hint" },
        el("span", { class: "swatch", style: `background:${seriesColor(result.approach.key)}` }),
        el("strong", {}, result.approach.label), " · ta demande : ",
        el("span", { class: "query-text" }, result.query_text)
      )
    ),
    // Mini tableau de bord de cette recherche
    el("div", { class: "tiles" },
      tile("Temps de calcul", formatMs(result.timing.algo_ms), "méthode seule"),
      tile("Temps serveur total", formatMs(result.timing.total_ms), "calcul + base de données"),
      tile("Moyenne de la méthode", formatMs(measured ? measured.algo_ms.mean : null),
        measured ? `sur ${formatNumber(measured.algo_ms.count)} recherche(s) O2` : null),
      tile("Fiches comparées", formatNumber(result.corpus_size), "taille de la base")
    )
  );

  if (result.count === 0) {
    results.append(el("p", { class: "placeholder" },
      "Aucune fiche ne respecte tous tes critères. La méthode heuristique élimine une fiche dès qu'un critère manque : retire un critère, ou ",
      el("a", { href: TWIN_PAGE }, "refais la recherche avec la méthode vectorielle"),
      ", qui propose toujours les fiches les plus proches."));
    return;
  }

  const { box, canvas } = chartBox(
    "Score des plantes recommandées",
    "Les scores des deux méthodes ne se calculent pas de la même façon : compare les classements, pas les valeurs.",
    Math.max(140, 28 * result.count + 60)
  );
  results.append(box);
  scoreChart = drawScoreChart(canvas, result.results, result.approach.key);

  results.append(
    el("p", { class: "hint" }, "Clique sur une fiche pour ouvrir la page de la plante."),
    el("div", { class: "card-grid" }, result.results.map((item) => resultCard(item, result.approach)))
  );
}

// ----- Démarrage -----

async function start() {
  try {
    const [approaches, criteria, categories] = await Promise.all([
      api.approaches(), api.options(), api.categories(),
    ]);
    approach = approaches.items.find((item) => item.key === APPROACH_KEY);
    approach.explanation = approach.explanations.environment;
    options = criteria;

    buildMethodBanner(approaches.items);
    buildCriteriaFields();
    const categorySelect = document.getElementById("field-category");
    for (const category of categories.items) {
      if (category.plant_count > 0) {
        categorySelect.append(el("option", { value: category.slug }, `${category.name} (${category.plant_count})`));
      }
    }
    restoreForms();

    careForm.addEventListener("submit", onCareSubmit);
    environmentForm.addEventListener("submit", onEnvironmentSubmit);
    environmentForm.addEventListener("reset", () => {
      // après la remise à zéro du navigateur, on remet les curseurs à jour
      setTimeout(() => environmentForm.querySelectorAll("input[name^=use_]").forEach((input) => input.dispatchEvent(new Event("change"))), 0);
    });
  } catch (error) {
    // l'erreur (API injoignable) est déjà affichée dans le bandeau par layout.js
    clear(document.getElementById("method-banner")).append(el("p", { class: "error" }, error.message));
  }
}

start();
