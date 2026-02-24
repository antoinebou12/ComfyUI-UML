/**
 * SVG view: renders SVG diagram content into the shell's container.
 * Used when format is "svg". Loaded only when needed.
 * Returns a Promise for uniform API with pngView (resolves immediately).
 */
export function render(container, data) {
  if (!container || typeof data !== "string") return Promise.resolve();
  const parser = new DOMParser();
  const doc = parser.parseFromString(data, "image/svg+xml");
  const svg = doc.documentElement;
  if (!svg || !svg.tagName || svg.tagName.toLowerCase() !== "svg") {
    return Promise.reject(new Error("Invalid SVG received."));
  }
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  viewport.appendChild(svg);
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  return Promise.resolve();
}
