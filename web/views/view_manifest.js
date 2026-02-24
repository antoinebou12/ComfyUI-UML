/**
 * View registry for the diagram viewer (ComfyUI_Viewer-style).
 * Only the selected view module is loaded via dynamic import().
 */
export const VIEW_MANIFEST = [
  { id: "svg", priority: 100, load: () => import("./svgView.mjs") },
  { id: "png", priority: 90, load: () => import("./pngView.mjs") },
  { id: "pdf", priority: 85, load: () => import("./pdfView.mjs") },
  { id: "txt", priority: 80, load: () => import("./txtView.mjs") },
  { id: "base64", priority: 75, load: () => import("./base64View.mjs") },
  { id: "iframe", priority: 70, load: () => import("./iframeView.mjs") },
  { id: "markdown", priority: 65, load: () => import("./markdownView.mjs") },
];

export function getViewDescriptor(format) {
  const id = (format || "svg").toString().toLowerCase().trim();
  if (id === "jpeg") return VIEW_MANIFEST.find((v) => v.id === "png");
  return VIEW_MANIFEST.find((v) => v.id === id) || VIEW_MANIFEST.find((v) => v.id === "svg");
}
