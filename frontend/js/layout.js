// En-tête, menu et pied de page communs à toutes les pages.
// Chaque page a <body data-page="..."> : c'est ce qui indique l'onglet actif.
import { api } from "./api.js";
import { el } from "./dom.js";

const PAGES = [
  ["home-heuristic", "index.html", "Accueil · méthode heuristique"],
  ["home-vector", "vectorielle.html", "Accueil · méthode vectorielle"],
  ["dashboard", "tableau-de-bord.html", "Tableau de bord"],
  ["team", "equipe.html", "L'équipe"],
];

function showBanner(message) {
  const banner = document.getElementById("status-banner");
  banner.textContent = message;
  banner.hidden = false;
}

function buildHeader() {
  const current = document.body.dataset.page;
  document.getElementById("site-header").append(
    el("div", { class: "brand" },
      el("a", { href: "index.html", class: "brand-name" }, "Raise a Plant"),
      el("p", { class: "tagline" }, "« Pourquoi acheter un 10, quand tu peux en faire pousser dix ? »")
    ),
    el("nav", { class: "tabs", "aria-label": "Navigation principale" },
      PAGES.map(([page, file, label]) =>
        el("a", { href: file, class: page === current ? "tab is-active" : "tab" }, label))
    )
  );
  document.getElementById("site-footer").append(
    "Données : ",
    el("a", { href: "https://plants.windrivergreens.com", target: "_blank", rel: "noopener" }, "Wind River Greens"),
    " (CC BY 4.0) · Photos : ",
    el("a", { href: "https://commons.wikimedia.org", target: "_blank", rel: "noopener" }, "Wikimedia Commons")
  );
}

/** Vérifie que l'API répond et que la base contient des plantes. */
async function checkApi() {
  try {
    const health = await api.health();
    if (health.plant_count === 0) {
      showBanner("La base de données est vide. Dans le dossier backend, lance : python prepa_db.py");
    }
    const version = document.getElementById("about-version");
    if (version) {
      version.textContent = `Version de l'API : ${health.version} · ${health.plant_count} plantes en base.`;
    }
  } catch (error) {
    showBanner(error.message);
  }
}

buildHeader();
checkApi();
