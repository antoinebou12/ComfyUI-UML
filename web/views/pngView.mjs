/**
 * PNG (raster image) view: renders image blob into the shell's container.
 * Used when format is "png" or "jpeg". Loaded only when needed.
 * Returns a Promise that resolves when the image has loaded (for shell to run fitToView etc.).
 */
export function render(container, data) {
  if (!container || !(data instanceof Blob)) return Promise.resolve();
  const img = document.createElement("img");
  img.alt = "Diagram";
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  viewport.appendChild(img);
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  img.src = URL.createObjectURL(data);
  return new Promise((resolve) => {
    img.onload = () => resolve();
    img.onerror = () => resolve();
  });
}
