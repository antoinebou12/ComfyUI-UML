/**
 * PNG (raster image) view: renders image blob into the shell's container.
 * Used when format is "png" or "jpeg". Loaded only when needed.
 * Returns a Promise that resolves when the image has loaded (for shell to run fitToView etc.).
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
  if (!container || !(data instanceof Blob)) return Promise.resolve();
  const viewport = _buildContainer(container);
  const img = document.createElement("img");
  img.alt = "Diagram";
  viewport.appendChild(img);
  img.src = URL.createObjectURL(data);
  return new Promise((resolve) => {
    img.onload = () => resolve();
    img.onerror = () => resolve();
  });
}
