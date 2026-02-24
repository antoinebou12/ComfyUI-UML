/**
 * PDF view: renders PDF blob into the shell's container using native browser PDF display.
 * Uses <object type="application/pdf"> so pan/zoom and Fit apply; no PDF.js dependency.
 * Returns a Promise that resolves when the object has loaded (or on error) so the shell can run fitToView.
 */
export function render(container, data) {
  if (!container || !(data instanceof Blob)) return Promise.resolve();
  const obj = document.createElement("object");
  obj.type = "application/pdf";
  obj.data = URL.createObjectURL(data);
  obj.setAttribute("aria-label", "Diagram PDF");
  // Give the object a size so the pan-zoom layer has dimensions (browser PDF viewer may not expose intrinsic size).
  obj.style.minWidth = "800px";
  obj.style.minHeight = "600px";
  obj.style.width = "800px";
  obj.style.height = "600px";
  obj.style.display = "block";
  const viewport = document.createElement("div");
  viewport.className = "viewport";
  viewport.appendChild(obj);
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(viewport);
  container.innerHTML = "";
  container.appendChild(layer);
  return new Promise((resolve) => {
    obj.onload = () => resolve();
    obj.onerror = () => resolve();
  });
}
