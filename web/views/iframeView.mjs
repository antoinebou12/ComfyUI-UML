/**
 * Iframe view: shows a URL inside an iframe (no fetch).
 * Used when format is "iframe". Shell passes the url string as data.
 */
export function render(container, data) {
  if (!container) return Promise.resolve();
  const url = typeof data === "string" ? data.trim() : "";
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  viewport.style.cssText = "width:100%; min-height:400px; overflow:hidden;";
  const iframe = document.createElement("iframe");
  iframe.title = "Embedded content";
  iframe.style.cssText = "width:100%; height:100%; min-height:400px; border:1px solid var(--comfy-border,#666); border-radius:4px; background:var(--comfy-bg-node,#353535);";
  iframe.sandbox.add("allow-scripts", "allow-same-origin", "allow-forms", "allow-popups");
  if (url && (url.startsWith("http:") || url.startsWith("https:") || url.startsWith("data:"))) {
    iframe.src = url;
  } else {
    iframe.srcdoc = "<p style='color:var(--comfy-text); padding:16px;'>No valid URL provided. Use ?url=https://...&amp;format=iframe</p>";
  }
  viewport.appendChild(iframe);
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  return Promise.resolve();
}
