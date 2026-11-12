// Point d'entrée du frontend : navigation par onglets et démarrage des vues.
import { api } from "./api.js";
import { initRecommend } from "./recommend.js";
import { initDashboard, loadDashboard } from "./dashboard.js";
import { initCatalogue, showCatalogue } from "./catalogue.js";

const banner = document.getElementById("status-banner");

function showBanner(message) {
  banner.textContent = message;
  banner.hidden = false;
}

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => { view.hidden = view.id !== `view-${name}`; });
  document.querySelectorAll(".tab").forEach((tab) => { tab.classList.toggle("is-active", tab.dataset.view === name); });
  if (name === "dashboard") loadDashboard(); // toujours à jour quand on l'ouvre
  if (name === "catalogue") showCatalogue();
}

async function start() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => showView(tab.dataset.view));
  });
  initDashboard();

  try {
    const health = await api.health();
    document.getElementById("about-version").textContent = `Version de l'API : ${health.version} · ${health.plant_count} plantes en base.`;
    if (health.plant_count === 0) {
      showBanner("La base de données est vide. Dans le dossier backend, lance : flask --app run seed");
    }
    await Promise.all([initRecommend(), initCatalogue()]);
  } catch (error) {
    showBanner(error.message);
  }
}

start();
