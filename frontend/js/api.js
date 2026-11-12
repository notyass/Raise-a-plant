// Toutes les requêtes HTTP vers le backend passent par ce fichier.
import { API_BASE_URL } from "./config.js";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(API_BASE_URL + path, options);
  } catch (networkError) {
    throw new Error(
      `Impossible de joindre l'API (${API_BASE_URL}). Le backend est-il lancé ?`
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch (parseError) {
    // Réponse sans JSON : on garde data = null.
  }

  if (!response.ok) {
    throw new Error((data && data.error) || `Erreur ${response.status}`);
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  options: () => request("/options"),
  approaches: () => request("/approaches"),
  categories: () => request("/categories"),
  metrics: () => request("/metrics"),
  plant: (id) => request(`/plants/${id}`),
  plants: (params) => request("/plants?" + new URLSearchParams(params).toString()),
  recommend: (body) =>
    request("/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
