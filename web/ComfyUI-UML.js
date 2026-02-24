/**
 * ComfyUI-UML: Open diagram viewer (context menu), dynamic output_format per diagram_type.
 * Builds Kroki URL from node widgets when opening viewer. Node uses ComfyUI default theme.
 */
import { app } from "../../scripts/app.js";

const SUPPORTED_FORMATS = {
  actdiag: ["png", "svg", "pdf"],
  blockdiag: ["png", "svg", "pdf"],
  bpmn: ["svg"],
  bytefield: ["svg"],
  c4plantuml: ["png", "svg", "pdf", "txt", "base64"],
  d2: ["png", "svg"],
  dbml: ["svg"],
  ditaa: ["png", "svg"],
  erd: ["png", "svg", "jpeg", "pdf"],
  excalidraw: ["svg"],
  graphviz: ["png", "svg", "pdf", "jpeg"],
  mermaid: ["svg", "png"],
  nomnoml: ["svg"],
  nwdiag: ["png", "svg", "pdf"],
  packetdiag: ["png", "svg", "pdf"],
  pikchr: ["svg"],
  plantuml: ["png", "svg", "pdf", "txt", "base64"],
  rackdiag: ["png", "svg", "pdf"],
  seqdiag: ["png", "svg", "pdf"],
  structurizr: ["png", "svg", "pdf", "txt", "base64"],
  svgbob: ["svg"],
  symbolator: ["svg"],
  tikz: ["png", "svg", "jpeg", "pdf"],
  umlet: ["png", "svg", "jpeg"],
  vega: ["png", "svg", "pdf"],
  vegalite: ["png", "svg", "pdf"],
  wavedrom: ["svg"],
  wireviz: ["png", "svg"],
};

function getViewerBaseUrl() {
  const base = new URL(document.baseURI || window.location.href);
  const path = base.pathname.replace(/\/$/, "");
  const extPath = path.includes("/extensions/")
    ? path.split("/extensions/")[0] + "/extensions/ComfyUI-UML"
    : "/extensions/ComfyUI-UML";
  return base.origin + extPath + "/viewer.html";
}

function getWidgetValue(node, name) {
  const w = node.widgets?.find((x) => x.name === name);
  return w != null ? w.value : undefined;
}

/** Deflate (raw) + base64url for Kroki GET URL. Uses CompressionStream when available. */
async function deflateBase64Url(text) {
  if (!text || typeof text !== "string") return "";
  const bytes = new TextEncoder().encode(text);
  if (typeof CompressionStream === "undefined") return null;
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"));
  const chunks = [];
  const reader = stream.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const total = chunks.reduce((acc, c) => acc + c.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  let b64 = "";
  try {
    b64 = btoa(String.fromCharCode.apply(null, out));
  } catch {
    return null;
  }
  return b64.replace(/\+/g, "-").replace(/\//g, "_");
}

function optionsToQuery(options) {
  if (!options || typeof options !== "object") return "";
  const parts = [];
  for (const [k, v] of Object.entries(options)) {
    if (v === true || v === "") parts.push([k, ""]);
    else parts.push([k, String(v)]);
  }
  if (parts.length === 0) return "";
  return "?" + new URLSearchParams(parts).toString();
}

/**
 * Build Kroki GET URL from current node widget values. Returns null if build fails.
 */
async function buildKrokiUrlFromNode(node) {
  const code = getWidgetValue(node, "code");
  const diagramType = (getWidgetValue(node, "diagram_type") || "mermaid").toString().toLowerCase().trim();
  const outputFormat = (getWidgetValue(node, "output_format") || "svg").toString().toLowerCase().trim();
  const baseUrl = (getWidgetValue(node, "kroki_url") || "https://kroki.io").toString().replace(/\/$/, "");
  const diagramOptionsStr = getWidgetValue(node, "diagram_options");

  const formats = SUPPORTED_FORMATS[diagramType] || ["png", "svg"];
  if (!formats.includes(outputFormat)) return null;
  const source = (code != null ? String(code) : "").trim();
  if (!source) return null;

  let options = null;
  if (diagramOptionsStr != null && String(diagramOptionsStr).trim()) {
    try {
      const parsed = JSON.parse(String(diagramOptionsStr).trim());
      if (parsed && typeof parsed === "object") options = parsed;
    } catch (_) {}
  }

  const encoded = await deflateBase64Url(source);
  if (encoded == null) return null;

  const query = optionsToQuery(options);
  return `${baseUrl}/${diagramType}/${outputFormat}/${encoded}${query}`;
}

function applyFormatsForType(node, diagramType) {
  const typeKey = (diagramType || "").toLowerCase().trim();
  const formats = SUPPORTED_FORMATS[typeKey] || ["png", "svg"];
  const formatWidget = node.widgets?.find((w) => w.name === "output_format");
  if (formatWidget && Array.isArray(formatWidget.options)) {
    formatWidget.options = formats;
    if (!formats.includes(formatWidget.value)) {
      formatWidget.value = formats[0];
    }
  }
}

app.registerExtension({
  name: "ComfyUI-UML.viewer",
  getNodeMenuItems(node) {
    if (node.comfyClass !== "UMLDiagram") return [];
    return [
      {
        content: "Open in viewer",
        callback: () => {
          buildKrokiUrlFromNode(node).then((krokiUrl) => {
            const base = getViewerBaseUrl();
            const target = krokiUrl ? base + "?url=" + encodeURIComponent(krokiUrl) : base;
            window.open(target, "_blank", "noopener");
          });
        },
      },
    ];
  },
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeType.comfyClass !== "UMLDiagram") return;
    if (nodeData.size == null) nodeData.size = [420, 320];
    const origOnResize = nodeType.prototype.onResize;
    nodeType.prototype.onResize = function (size) {
      const r = origOnResize?.apply(this, arguments);
      const dt = this.widgets?.find((w) => w.name === "diagram_type");
      if (dt) applyFormatsForType(this, dt.value);
      return r;
    };
  },
  async nodeCreated(node) {
    if (node.comfyClass !== "UMLDiagram") return;
    if (node.size && (node.size[0] < 420 || node.size[1] < 320)) {
      node.setSize([Math.max(420, node.size[0]), Math.max(320, node.size[1])]);
    }
    const diagramTypeWidget = node.widgets?.find((w) => w.name === "diagram_type");
    applyFormatsForType(node, diagramTypeWidget?.value ?? "mermaid");
    if (diagramTypeWidget) {
      const orig = diagramTypeWidget.callback;
      diagramTypeWidget.callback = function (value, app, node) {
        applyFormatsForType(node, value);
        if (orig) orig(value, app, node);
      };
    }
  },
});
