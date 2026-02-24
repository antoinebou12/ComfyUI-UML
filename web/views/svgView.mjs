/**
 * SVG view: renders SVG diagram content into the shell's container.
 * Used when format is "svg". Loaded only when needed.
 * On invalid SVG, shows raw content in a <pre> fallback instead of rejecting.
 */

function _buildContainer(container) {
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  return viewport;
}

export function render(container, data) {
  if (!container || typeof data !== "string") return Promise.resolve();
  const parser = new DOMParser();
  const doc = parser.parseFromString(data, "image/svg+xml");
  const svg = doc.documentElement;
  const viewport = _buildContainer(container);
  if (svg && svg.tagName && svg.tagName.toLowerCase() === "svg") {
    viewport.appendChild(svg);
    return Promise.resolve();
  }
  const pre = document.createElement("pre");
  pre.style.cssText =
    "margin:0; padding:16px; white-space:pre-wrap; color:var(--comfy-text,#AAA); font-size:13px; overflow:auto;";
  pre.textContent = typeof data === "string" ? data : "(invalid or empty content)";
  viewport.appendChild(pre);
  return Promise.resolve();
}
