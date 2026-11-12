// Petits outils pour construire la page sans innerHTML : le texte venant de
// l'API est toujours inséré comme texte, jamais interprété comme du HTML.

/** Crée un élément : el("p", { class: "hint" }, "Bonjour") */
export function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") node.className = value;
    else if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
    else if (name === "style") node.style.cssText = value;
    else node.setAttribute(name, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

export function clear(node) {
  node.replaceChildren();
  return node;
}

/** Affiche une durée en millisecondes : 0.42 ms, 12.3 ms, 1 250 ms */
export function formatMs(value) {
  if (value === null || value === undefined) return "—";
  const digits = value < 10 ? 2 : value < 100 ? 1 : 0;
  return value.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits }) + " ms";
}

export function formatNumber(value) {
  return value === null || value === undefined ? "—" : value.toLocaleString("fr-FR");
}

/** Une tuile « chiffre clé » */
export function tile(label, value, note) {
  return el("div", { class: "tile" },
    el("div", { class: "tile-label" }, label),
    el("div", { class: "tile-value" }, value),
    note ? el("div", { class: "tile-note" }, note) : null
  );
}
