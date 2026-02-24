/**
 * Plain text view: renders text (e.g. Kroki txt / ASCII art) in a scrollable container.
 * Used when format is "txt". Loaded only when needed.
 */
export function render(container, data) {
  if (!container) return Promise.resolve();
  const text = typeof data === "string" ? data : String(data ?? "");
  const pre = document.createElement("pre");
  pre.style.cssText =
    "margin:0; padding:16px; white-space:pre-wrap; word-break:break-word; " +
    "color:var(--comfy-text, #AAA); font-family:monospace; font-size:13px; " +
    "overflow:auto; max-width:100%; max-height:100%; box-sizing:border-box;";
  pre.textContent = text || "(empty)";
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  viewport.style.cssText = "overflow:auto; min-width:200px; min-height:120px;";
  viewport.appendChild(pre);
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  return Promise.resolve();
}
