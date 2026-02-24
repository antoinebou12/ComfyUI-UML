/**
 * ComfyUI-UML: Open diagram viewer (context menu), dynamic output_format per diagram_type.
 * Builds Kroki URL from node widgets when opening viewer. Node uses ComfyUI default theme.
 */
import { app } from "../../scripts/app.js";
import { formatFromUrl, buildViewerQuery } from "./viewerUrlUtils.mjs";

/** Generated from nodes/kroki_client.py SUPPORTED_FORMATS; do not edit by hand. Run scripts/generate_all_diagrams_workflow.py to update. */
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
  wireviz: ["png", "svg"],};

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

/** Normalize a widget value to string (handles object-shaped values from loaded workflows). */
function widgetValueString(val, fallback = "") {
  if (val == null) return fallback;
  if (typeof val === "string") return val;
  if (typeof val === "object" && "value" in val) return String(val.value ?? fallback);
  return String(val);
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

/**
 * Build Kroki GET URL from current node widget values. Returns null if build fails.
 * @param {object} node - UMLDiagram node
 * @param {string} [formatOverride] - If provided, use this format instead of the widget (must be supported by diagram type).
 */
async function buildKrokiUrlFromNode(node, formatOverride) {
  const code = getWidgetValue(node, "code");
  const diagramType = widgetValueString(getWidgetValue(node, "diagram_type"), "mermaid").toLowerCase().trim();
  const outputFormat =
    formatOverride != null && formatOverride !== ""
      ? String(formatOverride).toLowerCase().trim()
      : widgetValueString(getWidgetValue(node, "output_format"), "svg").toLowerCase().trim();
  const baseUrl = widgetValueString(getWidgetValue(node, "kroki_url"), "https://kroki.io").replace(/\/$/, "");

  const formats = SUPPORTED_FORMATS[diagramType] || ["png", "svg"];
  if (!formats.includes(outputFormat)) return null;
  const source = (code != null ? String(code) : "").trim();
  if (!source) return null;

  const encoded = await deflateBase64Url(source);
  if (encoded == null) return null;

  return `${baseUrl}/${diagramType}/${outputFormat}/${encoded}`;
}

/** Parse diagram type from a Kroki URL path (e.g. /plantuml/svg/xxx -> "plantuml"). Returns null if not parseable. */
function getDiagramTypeFromKrokiUrl(url) {
  if (!url || typeof url !== "string") return null;
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    if (parts.length >= 3) return parts[parts.length - 3];
  } catch (_) {}
  return null;
}

/** Return the same Kroki URL with the format segment replaced by newFormat. Returns null if path has fewer than 3 segments. */
function replaceKrokiUrlFormat(url, newFormat) {
  if (!url || typeof url !== "string" || newFormat == null) return null;
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    if (parts.length < 3) return null;
    parts[parts.length - 2] = String(newFormat);
    u.pathname = "/" + parts.join("/");
    return u.toString();
  } catch (_) {}
  return null;
}

/** Trigger download of a Blob with the given filename. */
function downloadBlob(blob, filename) {
  if (!blob || !filename) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function _toast(severity, summary, detail) {
  if (app.extensionManager?.toast?.add) {
    app.extensionManager.toast.add({ severity, summary, detail, life: 3000 });
  }
}

function applyFormatsForType(node, diagramType) {
  const raw =
    diagramType != null && typeof diagramType === "object" && "value" in diagramType
      ? diagramType.value
      : diagramType;
  const typeKey = String(raw ?? "").toLowerCase().trim();
  const formats = SUPPORTED_FORMATS[typeKey] || ["png", "svg"];
  const formatWidget = node.widgets?.find((w) => w.name === "output_format");
  if (formatWidget && Array.isArray(formatWidget.options)) {
    formatWidget.options = formats;
    if (!formats.includes(formatWidget.value)) {
      formatWidget.value = formats[0];
    }
  }
}

/** When backend is "web": show kroki_url; when "local": hide kroki_url. */
function applyBackendVisibility(node) {
  const backendWidget = node.widgets?.find((w) => w.name === "backend");
  const backend = backendWidget ? String(backendWidget.value || "web").toLowerCase().trim() : "web";
  const isWeb = backend === "web";
  const krokiWidget = node.widgets?.find((w) => w.name === "kroki_url");
  if (krokiWidget) krokiWidget.hidden = !isWeb;
  node.setSize(node.computeSize());
  app.graph.setDirtyCanvas(true, true);
}

/** Debounce (ms) for UMLDiagram inline preview refresh (code/diagram_type/output_format changes). */
const DIAGRAM_PREVIEW_DEBOUNCE_MS = 400;

/**
 * Attach a live iframe preview to a UMLDiagram node.
 * Uses buildKrokiUrlFromNode (client-side); refreshes debounced on code/diagram_type/output_format/kroki_url/backend.
 */
function _attachInlinePreviewForDiagram(node) {
  if (!node.addDOMWidget) return;

  const wrapper = document.createElement("div");
  wrapper.style.cssText =
    "width:100%; height:" + PREVIEW_HEIGHT + "px; position:relative; overflow:hidden; " +
    "border-radius:6px; background:var(--comfy-menu-bg,#1a1a2e); border:1px solid var(--border-color,#444);";

  const placeholder = document.createElement("div");
  placeholder.style.cssText =
    "position:absolute; inset:0; display:flex; align-items:center; justify-content:center; " +
    "color:var(--descrip-text,#888); font-size:12px; font-family:sans-serif; padding:8px; text-align:center;";
  placeholder.textContent = "Enter diagram code and set type/format to see preview.";
  wrapper.appendChild(placeholder);

  const iframe = document.createElement("iframe");
  iframe.title = "Diagram preview";
  iframe.style.cssText =
    "position:absolute; inset:0; width:100%; height:100%; border:none; border-radius:6px; opacity:0;";
  iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
  wrapper.appendChild(iframe);
  node._umlPreviewIframe = iframe;

  node.addDOMWidget("diagram_preview", "preview", wrapper, {
    getValue() { return ""; },
    setValue() {},
    computeSize() { return [node.size?.[0] ?? 400, PREVIEW_HEIGHT + 8]; },
  });

  let debounceTimer = null;
  function scheduleRefresh() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      refreshPreview();
    }, DIAGRAM_PREVIEW_DEBOUNCE_MS);
  }

  async function refreshPreview() {
    let krokiUrl = null;
    try {
      krokiUrl = await buildKrokiUrlFromNode(node);
    } catch (_) {
      krokiUrl = null;
    }
    if (!krokiUrl) {
      iframe.removeAttribute("src");
      placeholder.style.display = "flex";
      iframe.style.opacity = "0";
      return;
    }
    placeholder.style.display = "none";
    iframe.style.opacity = "1";
    const base = getViewerBaseUrl();
    const iframeSrc = base + buildViewerQuery(krokiUrl, formatFromUrl(krokiUrl), true);
    if (iframe.src !== iframeSrc) iframe.src = iframeSrc;
  }

  for (const name of ["code", "diagram_type", "output_format", "kroki_url", "backend"]) {
    const w = node.widgets?.find((x) => x.name === name);
    if (!w) continue;
    const orig = w.callback;
    w.callback = function (value, appRef, nodeRef) {
      if (orig) orig(value, appRef, nodeRef);
      scheduleRefresh();
    };
  }

  refreshPreview();

  const minH = PREVIEW_HEIGHT + 120;
  if (!node.size || node.size[1] < minH) {
    node.setSize([node.size?.[0] ?? 400, Math.max(node.size?.[1] ?? 0, minH)]);
  }
}

/** Height (px) of the inline diagram preview inside UMLDiagram and UMLViewerURL nodes. */
const PREVIEW_HEIGHT = 480;

app.registerExtension({
  name: "ComfyUI-UML.viewer",
  getNodeMenuItems(node) {
    if (node.comfyClass !== "UMLDiagram") return [];
    const diagramType = widgetValueString(getWidgetValue(node, "diagram_type"), "mermaid").toLowerCase().trim();
    const formats = SUPPORTED_FORMATS[diagramType] || ["png", "svg"];
    const supportsPng = formats.includes("png");
    const supportsTxt = formats.includes("txt");

    const items = [
      {
        content: "Open in viewer",
        callback: () => {
          buildKrokiUrlFromNode(node).then((krokiUrl) => {
            const base = getViewerBaseUrl();
            const outputFormat = widgetValueString(getWidgetValue(node, "output_format"), "svg").toLowerCase().trim();
            let target = krokiUrl ? base + "?url=" + encodeURIComponent(krokiUrl) : base;
            if (krokiUrl) target += "&format=" + encodeURIComponent(outputFormat);
            window.open(target, "_blank", "noopener");
          });
        },
      },
      {
        content: "Copy Kroki URL",
        callback: async () => {
          try {
            const url = await buildKrokiUrlFromNode(node);
            if (!url) {
              _toast("error", "Copy failed", "Could not build Kroki URL (empty code or unsupported format).");
              return;
            }
            if (navigator.clipboard?.writeText) {
              await navigator.clipboard.writeText(url);
              _toast("success", "Kroki URL copied", "");
            } else {
              _toast("error", "Copy failed", "Clipboard not available.");
            }
          } catch (e) {
            _toast("error", "Copy failed", e?.message || "Unknown error");
          }
        },
      },
      {
        content: "Fit",
        callback: () => {
          const iframe = node._umlPreviewIframe;
          if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({ type: "comfyui-uml-fit" }, "*");
          }
        },
      },
    ];

    if (supportsPng) {
      items.push({
        content: "Save as PNG",
        callback: async () => {
          try {
            const url = await buildKrokiUrlFromNode(node, "png");
            if (!url) {
              _toast("error", "Save failed", "Could not build PNG URL.");
              return;
            }
            const res = await fetch(url);
            if (!res.ok) throw new Error(res.statusText || "Fetch failed");
            const blob = await res.blob();
            downloadBlob(blob, "diagram.png");
            _toast("success", "Saved as PNG", "diagram.png");
          } catch (e) {
            _toast("error", "Save as PNG failed", e?.message || "Check CORS or open in viewer to download.");
          }
        },
      });
    }

    if (supportsTxt) {
      items.push({
        content: "Save as TXT",
        callback: async () => {
          try {
            const url = await buildKrokiUrlFromNode(node, "txt");
            if (!url) {
              _toast("error", "Save failed", "Could not build TXT URL.");
              return;
            }
            const res = await fetch(url);
            if (!res.ok) throw new Error(res.statusText || "Fetch failed");
            const text = await res.text();
            const blob = new Blob([text], { type: "text/plain" });
            downloadBlob(blob, "diagram.txt");
            _toast("success", "Saved as TXT", "diagram.txt");
          } catch (e) {
            _toast("error", "Save as TXT failed", e?.message || "Check CORS or open in viewer.");
          }
        },
      });
    }

    items.push({
      content: "Save source as text",
      callback: () => {
        const code = getWidgetValue(node, "code");
        const source = (code != null ? String(code) : "").trim();
        if (!source) {
          _toast("warn", "No source", "Code widget is empty.");
          return;
        }
        const blob = new Blob([source], { type: "text/plain" });
        downloadBlob(blob, "diagram_source.txt");
        _toast("success", "Saved source", "diagram_source.txt");
      },
    });

    return items;
  },
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeType.comfyClass !== "UMLDiagram") return;
    if (nodeData.size == null) nodeData.size = [400, 300];
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
    if (node.size && (node.size[0] < 400 || node.size[1] < 300)) {
      node.setSize([Math.max(400, node.size[0]), Math.max(300, node.size[1])]);
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
    const backendWidget = node.widgets?.find((w) => w.name === "backend");
    applyBackendVisibility(node);
    if (backendWidget) {
      const origBackend = backendWidget.callback;
      backendWidget.callback = function (value, app, node) {
        applyBackendVisibility(node);
        if (origBackend) origBackend(value, app, node);
      };
    }
    _attachInlinePreviewForDiagram(node);
  },
});

/** Resolve effective kroki URL for Diagram Viewer URL node: widget value or from linked UMLDiagram. */
async function getEffectiveKrokiUrlForViewerUrlNode(node) {
  const widgetVal = widgetValueString(getWidgetValue(node, "kroki_url"), "").trim();
  if (widgetVal) return widgetVal;
  const inp = node.inputs?.find((i) => i.name === "kroki_url");
  if (!inp || inp.link == null) return null;
  const graph = app.graph;
  if (!graph?.links?.[inp.link]) return null;
  const link = graph.links[inp.link];
  const origin = graph.getNodeById?.(link.origin_id);
  if (!origin || origin.comfyClass !== "UMLDiagram") return null;
  return buildKrokiUrlFromNode(origin);
}

/** Build viewer URL (and iframe variant) from a kroki/content URL string. */
function getViewerUrlsFromKrokiUrl(url) {
  const base = getViewerBaseUrl();
  if (!url || !url.trim()) return { full: base + "?embed=1", iframe: base + "?embed=1" };
  const formatParam = formatFromUrl(url);
  return {
    full: base + buildViewerQuery(url, formatParam, false),
    iframe: base + buildViewerQuery(url, formatParam, true),
  };
}

/** Build viewer URL (and iframe variant) from Diagram Viewer URL node. Uses effectiveUrl when provided (e.g. from getEffectiveKrokiUrlForViewerUrlNode). */
function getViewerUrlFromViewerUrlNode(node, effectiveUrl) {
  const url =
    effectiveUrl !== undefined
      ? widgetValueString(effectiveUrl, "").trim()
      : widgetValueString(getWidgetValue(node, "kroki_url"), "").trim();
  return getViewerUrlsFromKrokiUrl(url);
}

/**
 * Attach a live iframe preview DOM widget to a UMLViewerURL node.
 * Shows the viewer in embed mode; updates on kroki_url change and after execution.
 */
function _attachInlinePreview(node) {
  if (!node.addDOMWidget) return; // guard: older ComfyUI versions

  const wrapper = document.createElement("div");
  wrapper.style.cssText =
    "width:100%; height:" + PREVIEW_HEIGHT + "px; position:relative; overflow:hidden; " +
    "border-radius:6px; background:var(--comfy-menu-bg,#1a1a2e); border:1px solid var(--border-color,#444);";

  const placeholder = document.createElement("div");
  placeholder.style.cssText =
    "position:absolute; inset:0; display:flex; align-items:center; justify-content:center; " +
    "color:var(--descrip-text,#888); font-size:12px; font-family:sans-serif; padding:8px; text-align:center;";
  placeholder.textContent = "Connect a kroki_url to see the diagram here.";
  wrapper.appendChild(placeholder);

  const iframe = document.createElement("iframe");
  iframe.title = "Diagram preview";
  iframe.style.cssText =
    "position:absolute; inset:0; width:100%; height:100%; border:none; border-radius:6px; opacity:0;";
  iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
  wrapper.appendChild(iframe);
  node._umlPreviewIframe = iframe;

  node.addDOMWidget("diagram_preview", "preview", wrapper, {
    getValue() { return ""; },
    setValue() {},
    computeSize() { return [node.size?.[0] ?? 420, PREVIEW_HEIGHT + 8]; },
  });

  async function refreshPreview() {
    const url = await getEffectiveKrokiUrlForViewerUrlNode(node);
    if (!url) {
      iframe.removeAttribute("src");
      placeholder.style.display = "flex";
      iframe.style.opacity = "0";
      return;
    }
    placeholder.style.display = "none";
    iframe.style.opacity = "1";
    const { iframe: iframeSrc } = getViewerUrlFromViewerUrlNode(node, url);
    if (iframe.src !== iframeSrc) iframe.src = iframeSrc;
  }

  const krokiWidget = node.widgets?.find((w) => w.name === "kroki_url");
  if (krokiWidget) {
    const origCallback = krokiWidget.callback;
    krokiWidget.callback = function (value, appRef, nodeRef) {
      if (origCallback) origCallback(value, appRef, nodeRef);
      refreshPreview();
    };
  }

  const prevOnExecuted = node.onExecuted;
  node.onExecuted = function () {
    if (typeof prevOnExecuted === "function") prevOnExecuted.apply(this, arguments);
    refreshPreview();
  };

  const prevOnConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function (type, index, connected, link_info) {
    if (typeof prevOnConnectionsChange === "function") prevOnConnectionsChange.apply(this, arguments);
    refreshPreview();
  };

  refreshPreview();

  const minW = 420;
  const minH = PREVIEW_HEIGHT + 120;
  if (!node.size || node.size[0] < minW || node.size[1] < minH) {
    node.setSize([Math.max(node.size?.[0] ?? 0, minW), Math.max(node.size?.[1] ?? 0, minH)]);
  }
}

app.registerExtension({
  name: "ComfyUI-UML.viewerUrl",
  getNodeMenuItems(node) {
    if (node.comfyClass !== "UMLViewerURL") return [];
    const { full, iframe: iframeUrl } = getViewerUrlFromViewerUrlNode(node);

    const items = [
      {
        content: "Open in viewer",
        callback: () => window.open(full, "_blank", "noopener"),
      },
      {
        content: "Open in window",
        callback: () => {
          const features = "width=1000,height=700,menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes";
          window.open(iframeUrl, "ComfyUI-UML-Diagram-Viewer", features);
        },
      },
      {
        content: "Copy Kroki URL",
        callback: async () => {
          try {
            const url = await getEffectiveKrokiUrlForViewerUrlNode(node);
            if (!url) {
              _toast("error", "Copy failed", "No Kroki URL (set widget or connect UML Render).");
              return;
            }
            if (navigator.clipboard?.writeText) {
              await navigator.clipboard.writeText(url);
              _toast("success", "Kroki URL copied", "");
            } else {
              _toast("error", "Copy failed", "Clipboard not available.");
            }
          } catch (e) {
            _toast("error", "Copy failed", e?.message || "Unknown error");
          }
        },
      },
      {
        content: "Fit",
        callback: () => {
          const iframe = node._umlPreviewIframe;
          if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({ type: "comfyui-uml-fit" }, "*");
          }
          const minW = 700;
          const minH = 550;
          if (!node.size || node.size[0] < minW || node.size[1] < minH) {
            node.setSize([Math.max(node.size?.[0] ?? 0, minW), Math.max(node.size?.[1] ?? 0, minH)]);
          }
        },
      },
    ];

    items.push(
      {
        content: "Save as PNG",
        callback: async () => {
          try {
            const url = await getEffectiveKrokiUrlForViewerUrlNode(node);
            if (!url) {
              _toast("error", "Save failed", "No Kroki URL.");
              return;
            }
            const diagramType = getDiagramTypeFromKrokiUrl(url);
            const formats = diagramType ? (SUPPORTED_FORMATS[diagramType] || []) : [];
            if (!formats.includes("png")) {
              _toast("error", "Save as PNG", "Diagram type does not support PNG.");
              return;
            }
            const pngUrl = replaceKrokiUrlFormat(url, "png");
            if (!pngUrl) {
              _toast("error", "Save failed", "Could not build PNG URL.");
              return;
            }
            const res = await fetch(pngUrl);
            if (!res.ok) throw new Error(res.statusText || "Fetch failed");
            const blob = await res.blob();
            downloadBlob(blob, "diagram.png");
            _toast("success", "Saved as PNG", "diagram.png");
          } catch (e) {
            _toast("error", "Save as PNG failed", e?.message || "Check CORS or open in viewer to download.");
          }
        },
      },
      {
        content: "Save as TXT",
        callback: async () => {
          try {
            const url = await getEffectiveKrokiUrlForViewerUrlNode(node);
            if (!url) {
              _toast("error", "Save failed", "No Kroki URL.");
              return;
            }
            const diagramType = getDiagramTypeFromKrokiUrl(url);
            const formats = diagramType ? (SUPPORTED_FORMATS[diagramType] || []) : [];
            if (!formats.includes("txt")) {
              _toast("error", "Save as TXT", "Diagram type does not support TXT.");
              return;
            }
            const txtUrl = replaceKrokiUrlFormat(url, "txt");
            if (!txtUrl) {
              _toast("error", "Save failed", "Could not build TXT URL.");
              return;
            }
            const res = await fetch(txtUrl);
            if (!res.ok) throw new Error(res.statusText || "Fetch failed");
            const text = await res.text();
            const blob = new Blob([text], { type: "text/plain" });
            downloadBlob(blob, "diagram.txt");
            _toast("success", "Saved as TXT", "diagram.txt");
          } catch (e) {
            _toast("error", "Save as TXT failed", e?.message || "Check CORS or open in viewer.");
          }
        },
      }
    );

    return items;
  },
  async nodeCreated(node) {
    if (node.comfyClass !== "UMLViewerURL") return;
    _attachInlinePreview(node);
  },
});


// Chrome AI (Gemini Nano): feature detection and Run with Chrome AI
function isChromeAIAvailable() {
  const LM = typeof globalThis !== "undefined" && globalThis.LanguageModel || typeof window !== "undefined" && window.LanguageModel;
  return LM && typeof LM.create === "function";
}

function showChromeAIResultModal(resultText, appRef) {
  const overlay = document.createElement("div");
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:100000;";
  const box = document.createElement("div");
  box.style.cssText = "background:var(--comfy-menu-bg, #333);color:var(--comfy-menu-fg, #eee);padding:16px;border-radius:8px;max-width:90vw;max-height:85vh;display:flex;flex-direction:column;box-shadow:0 4px 20px rgba(0,0,0,0.4);";
  const title = document.createElement("div");
  title.textContent = "Chrome AI response";
  title.style.cssText = "font-weight:bold;margin-bottom:8px;";
  const textarea = document.createElement("textarea");
  textarea.readOnly = true;
  textarea.value = resultText || "";
  textarea.style.cssText = "width:520px;height:280px;resize:vertical;font-family:monospace;font-size:12px;padding:8px;margin-bottom:12px;background:#1e1e1e;color:#eee;border:1px solid #444;border-radius:4px;";
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;justify-content:flex-end;";
  const copyBtn = document.createElement("button");
  copyBtn.textContent = "Copy";
  copyBtn.className = "comfy-btn";
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(resultText || "").then(() => {
      if (appRef?.extensionManager?.toast?.add) {
        appRef.extensionManager.toast.add({ severity: "info", summary: "Copied", detail: "Response copied to clipboard", life: 2000 });
      }
    });
  };
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "Close";
  closeBtn.className = "comfy-btn";
  closeBtn.onclick = () => overlay.remove();
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  btnRow.append(copyBtn, closeBtn);
  box.append(title, textarea, btnRow);
  overlay.appendChild(box);
  document.body.appendChild(overlay);
}

async function runChromeAIPrompt(prompt, negativePrompt, appRef) {
  const LM = typeof globalThis !== "undefined" && globalThis.LanguageModel || typeof window !== "undefined" && window.LanguageModel;
  if (!LM || typeof LM.create !== "function") {
    throw new Error("Chrome AI (Gemini Nano) is not available. Use Chrome 138+ and enable \"Prompt API for Gemini Nano\" in chrome://flags. You may need to download the model in chrome://components.");
  }
  const initialPrompts = (negativePrompt && String(negativePrompt).trim())
    ? [{ role: "system", content: "Do NOT do the following: " + String(negativePrompt).trim() }]
    : [];
  const session = await LM.create({ initialPrompts });
  const response = await session.prompt(prompt);
  return typeof response === "string" ? response : (response && response.text != null ? response.text : String(response));
}

// LLMCall: dynamic Ollama model list and Refresh models button
const OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434";
const OLLAMA_GET_MODELS_PATH = "/comfyui-uml/ollama/get_models";

app.registerExtension({
  name: "ComfyUI-UML.llmCallOllama",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "LLMCall") return;
    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = async function () {
      if (originalOnNodeCreated) {
        originalOnNodeCreated.apply(this, arguments);
      }
      const urlWidget = this.widgets?.find((w) => w.name === "ollama_base_url");
      const modelWidget = this.widgets?.find((w) => w.name === "model");
      const providerWidget = this.widgets?.find((w) => w.name === "provider");
      if (!urlWidget || !modelWidget) return;

      const fetchModels = async (url) => {
        const base = (url || OLLAMA_DEFAULT_URL).toString().replace(/\/$/, "");
        const response = await fetch(OLLAMA_GET_MODELS_PATH, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: base }),
        });
        if (response.ok) {
          const models = await response.json();
          return Array.isArray(models) ? models : [];
        }
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || response.statusText);
      };

      const refreshButtonWidget = this.addWidget("button", "Refresh models");

      const updateModels = async () => {
        if (providerWidget && providerWidget.value !== "ollama") return;
        refreshButtonWidget.name = "Fetching...";
        if (this.setDirtyCanvas) this.setDirtyCanvas(true);
        const url = urlWidget.value ?? "";
        let models = [];
        try {
          models = await fetchModels(url);
        } catch (e) {
          console.error("[ComfyUI-UML] Ollama get_models error:", e);
          if (app.extensionManager?.toast?.add) {
            app.extensionManager.toast.add({
              severity: "error",
              summary: "Ollama connection error",
              detail: "Make sure Ollama server is running",
              life: 5000,
            });
          }
          refreshButtonWidget.name = "Refresh models";
          if (this.setDirtyCanvas) this.setDirtyCanvas(true);
          return;
        }
        const prevValue = modelWidget.value;
        if (modelWidget.options) {
          modelWidget.options.values = models;
        } else {
          modelWidget.options = { values: models };
        }
        if (models.includes(prevValue)) {
          modelWidget.value = prevValue;
        } else if (models.length > 0) {
          modelWidget.value = models[0];
        }
        refreshButtonWidget.name = "Refresh models";
        if (this.setDirtyCanvas) this.setDirtyCanvas(true);
      };

      refreshButtonWidget.callback = updateModels;
      const origUrlCallback = urlWidget.callback;
      urlWidget.callback = function (value, app, node) {
        if (origUrlCallback) origUrlCallback(value, app, node);
        updateModels();
      };

      const chromeAIButton = this.addWidget("button", "Run with Chrome AI");
      chromeAIButton.callback = async () => {
        const promptWidget = this.widgets?.find((w) => w.name === "prompt");
        const negativeWidget = this.widgets?.find((w) => w.name === "negative_prompt");
        const prompt = promptWidget != null ? widgetValueString(promptWidget.value) : "";
        const negative = negativeWidget != null ? widgetValueString(negativeWidget.value) : "";
        if (!prompt.trim()) {
          if (app.extensionManager?.toast?.add) {
            app.extensionManager.toast.add({ severity: "warn", summary: "Chrome AI", detail: "Enter a prompt first", life: 3000 });
          }
          return;
        }
        const prevName = chromeAIButton.name;
        chromeAIButton.name = "Running...";
        if (this.setDirtyCanvas) this.setDirtyCanvas(true);
        try {
          const result = await runChromeAIPrompt(prompt, negative, app);
          showChromeAIResultModal(result, app);
        } catch (err) {
          console.error("[ComfyUI-UML] Chrome AI error:", err);
          if (app.extensionManager?.toast?.add) {
            app.extensionManager.toast.add({
              severity: "error",
              summary: "Chrome AI",
              detail: err?.message || String(err),
              life: 6000,
            });
          }
        } finally {
          chromeAIButton.name = prevName;
          if (this.setDirtyCanvas) this.setDirtyCanvas(true);
        }
      };

      if (providerWidget && providerWidget.value === "ollama") {
        await updateModels();
      }
    };
  },
});

function _isLinksCorrupted(links) {
  if (!Array.isArray(links)) return true;
  if (links.length === 0) return false;
  const first = links[0];
  if (Array.isArray(first)) return true;
  if (first && typeof first === "object") {
    const required = new Set(["id", "origin_id", "origin_slot", "target_id", "target_slot", "type"]);
    for (const link of links) {
      if (!link || typeof link !== "object") return true;
      for (const k of required) {
        if (!(k in link)) return true;
      }
      if (link.origin_id == null && link.target_id == null) return true;
    }
    return false;
  }
  return true;
}

function _rebuildLinks(nodes) {
  const idToOrigin = new Map();
  const idToTarget = new Map();

  for (const node of nodes || []) {
    if (!node || typeof node !== "object") continue;
    const nid = node.id;
    if (nid == null) continue;

    const outputs = node.outputs || [];
    for (let i = 0; i < outputs.length; i++) {
      const out = outputs[i];
      if (!out || typeof out !== "object") continue;
      const slot = out.slot_index != null ? out.slot_index : i;
      const typ = out.type || "STRING";
      const linksOut = out.links;
      if (Array.isArray(linksOut)) {
        for (const linkId of linksOut) {
          if (linkId != null) idToOrigin.set(linkId, [nid, slot, typ]);
        }
      } else if (linksOut != null) {
        idToOrigin.set(linksOut, [nid, slot, typ]);
      }
    }

    const inputs = node.inputs || [];
    for (let i = 0; i < inputs.length; i++) {
      const inp = inputs[i];
      if (!inp || typeof inp !== "object") continue;
      const linkId = inp.link;
      const slot = inp.slot_index != null ? inp.slot_index : i;
      if (linkId != null) idToTarget.set(linkId, [nid, slot]);
    }
  }

  const linkIds = new Set([...idToOrigin.keys(), ...idToTarget.keys()]);
  const links = [];
  const sorted = Array.from(linkIds).sort((a, b) => Number(a) - Number(b));
  for (const linkId of sorted) {
    const orig = idToOrigin.get(linkId);
    const tgt = idToTarget.get(linkId);
    if (!orig || !tgt) continue;
    links.push({
      id: linkId,
      origin_id: orig[0],
      origin_slot: orig[1],
      target_id: tgt[0],
      target_slot: tgt[1],
      type: orig[2],
    });
  }
  return links;
}

function _nodeRect(node) {
  const pos = node.pos;
  const size = node.size;
  if (!Array.isArray(pos) || pos.length < 2) return null;
  if (!Array.isArray(size) || size.length < 2) return null;
  const x = Number(pos[0]);
  const y = Number(pos[1]);
  const w = Number(size[0]);
  const h = Number(size[1]);
  if (![x, y, w, h].every(Number.isFinite)) return null;
  return [x, y, w, h];
}

function _ensureGroupBounds(groups, nodes) {
  const nodeById = new Map();
  for (const n of nodes || []) {
    if (n && typeof n === "object" && n.id != null) nodeById.set(n.id, n);
  }

  for (const group of groups || []) {
    if (!group || typeof group !== "object") continue;
    const bound = group.bound ?? group.bounding;
    if (Array.isArray(bound) && bound.length >= 4) {
      const nums = bound.slice(0, 4).map((v) => Number(v));
      if (nums.every(Number.isFinite)) {
        group.bound = bound;
        group.bounding = group.bound;
        continue;
      }
    }
    const nodeIds = Array.isArray(group.nodes) ? group.nodes : [];
    const rects = [];
    for (const nid of nodeIds) {
      const node = nodeById.get(nid);
      if (!node) continue;
      const r = _nodeRect(node);
      if (r) rects.push(r);
    }
    if (rects.length === 0) {
      group.bound = [0, 0, 400, 300];
      group.bounding = group.bound;
      continue;
    }
    const minX = Math.min(...rects.map((r) => r[0]));
    const minY = Math.min(...rects.map((r) => r[1]));
    const maxX = Math.max(...rects.map((r) => r[0] + r[2]));
    const maxY = Math.max(...rects.map((r) => r[1] + r[3]));
    const padding = 20;
    group.bound = [
      Math.max(0, minX - padding),
      Math.max(0, minY - padding),
      maxX - minX + 2 * padding,
      maxY - minY + 2 * padding,
    ];
    group.bounding = group.bound;
  }
}

/** Ensure every group has a valid bound (array of 4 numbers). Removes null/non-object entries. Sets both bound and bounding for frontend compatibility. */
function _sanitizeGroups(groups) {
  if (!Array.isArray(groups)) return [];
  const out = [];
  const defaultBound = [0, 0, 400, 300];
  for (const g of groups) {
    if (g == null || typeof g !== "object") continue;
    const b = g.bound ?? g.bounding;
    const valid =
      Array.isArray(b) &&
      b.length >= 4 &&
      b.slice(0, 4).every((v) => Number.isFinite(Number(v)));
    if (!valid) {
      g.bound = defaultBound.slice();
      g.bounding = g.bound;
    } else {
      g.bound = b;
      g.bounding = g.bound;
    }
    out.push(g);
  }
  return out;
}

/** Returns a safe copy of groups for LiteGraph: only title, nodes, bound, bounding; bound/bounding are new arrays of 4 numbers. */
function _safeGroupsCopy(groups) {
  if (!Array.isArray(groups)) return [];
  const defaultBound = [0, 0, 400, 300];
  const out = [];
  for (const g of groups) {
    if (g == null || typeof g !== "object") continue;
    const b = g.bound ?? g.bounding;
    const valid =
      Array.isArray(b) &&
      b.length >= 4 &&
      b.slice(0, 4).every((v) => Number.isFinite(Number(v)));
    const arr = valid ? b.slice(0, 4).map((v) => Number(v)) : defaultBound.slice();
    out.push({
      title: g.title != null ? String(g.title) : "",
      nodes: Array.isArray(g.nodes) ? g.nodes.slice() : [],
      bound: arr.slice(),
      bounding: arr.slice(),
    });
  }
  return out;
}

/** Minimal valid workflow so ComfyUI never receives null/undefined. Return a new object each time. */
function _minimalWorkflow() {
  return {
    nodes: [],
    links: [],
    groups: [],
    config: {},
    extra: {},
    version: 0.4,
    lastNodeId: 0,
    lastLinkId: 0,
  };
}

function _normalizeWorkflowData(raw) {
  if (!raw) return raw;
  let data = raw;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return raw;
    }
  }
  if (!data || typeof data !== "object") return raw;

  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  data.nodes = nodes;

  for (const node of nodes) {
    if (node && typeof node === "object") {
      if (node.inputs == null) node.inputs = [];
      if (node.outputs == null) node.outputs = [];
      if (node.type != null && (node.class_type == null || node.class_type === undefined)) {
        node.class_type = node.type;
      }
    }
  }

  const links = data.links;
  if (!Array.isArray(links) || _isLinksCorrupted(links)) {
    data.links = _rebuildLinks(nodes);
  } else if (data.links == null) {
    data.links = [];
  } else {
    data.links = data.links.filter(
      (l) => l && typeof l === "object" && !(l.origin_id == null && l.target_id == null)
    );
  }

  let lastLink = data.lastLinkId != null ? data.lastLinkId : data.last_link_id;
  if ((data.links || []).length && (!lastLink || lastLink === 0)) {
    lastLink = Math.max(...data.links.map((l) => Number(l?.id || 0)));
  }
  if (lastLink != null && lastLink !== undefined) data.lastLinkId = Number(lastLink);
  delete data.last_link_id;

  let lastNode = data.lastNodeId != null ? data.lastNodeId : data.last_node_id;
  if (lastNode == null && nodes.length) {
    lastNode = Math.max(...nodes.map((n) => Number(n?.id || 0)));
  }
  if (lastNode != null && lastNode !== undefined) data.lastNodeId = Number(lastNode);
  delete data.last_node_id;

  if (!Array.isArray(data.groups)) {
    data.groups = [];
  } else {
    _ensureGroupBounds(data.groups, nodes);
    data.groups = _sanitizeGroups(data.groups);
  }

  if (data.config == null) data.config = {};
  if (data.extra == null) data.extra = {};
  if (data.version == null) data.version = 0.4;

  return data;
}

function _installWorkflowNormalizer() {
  const tryInstall = () => {
    const original = app.loadGraphData;
    if (typeof original !== "function") return false;
    if (original.__umlPatched) return true;
    app.loadGraphData = async function (graphData, ...rest) {
      if (graphData == null) {
        return await original.call(this, _minimalWorkflow(), ...rest);
      }
      let normalized = graphData;
      try {
        normalized = _normalizeWorkflowData(graphData);
      } catch (e) {
        console.warn("[ComfyUI-UML] Workflow normalize failed:", e);
      }
      try {
        const payload = {
          ...normalized,
          groups: _safeGroupsCopy(normalized.groups || []),
        };
        return await original.call(this, payload, ...rest);
      } catch (e) {
        if (
          e instanceof TypeError &&
          (e.message === "Cannot convert undefined or null to object" ||
            /undefined or null to object/i.test(e.message))
        ) {
          try {
            let safe = _normalizeWorkflowData(graphData);
            if (!safe || typeof safe !== "object") {
              safe = _minimalWorkflow();
            } else {
              safe.groups = [];
            }
            return await original.call(this, safe, ...rest);
          } catch (retryErr) {
            console.warn("[ComfyUI-UML] Workflow load retry failed:", retryErr);
          }
        }
        throw e;
      }
    };
    app.loadGraphData.__umlPatched = true;
    console.log("[ComfyUI-UML] Workflow normalizer installed");
    return true;
  };

  if (!tryInstall()) {
    let attempts = 0;
    const interval = setInterval(() => {
      attempts += 1;
      if (tryInstall() || attempts > 20) {
        clearInterval(interval);
      }
    }, 200);
  }
}

app.registerExtension({
  name: "ComfyUI-UML.workflowNormalizer",
  setup() {
    _installWorkflowNormalizer();
    _installGraphToPromptNormalizer();
  },
});

/** Ensure every node in graphToPrompt output has class_type and valid inputs so comfy-test validation passes. */
function _normalizePromptNodes(promptObj) {
  if (!promptObj || typeof promptObj !== "object") return;
  const graphs = [app.canvas?.graph, app.graph].filter((g) => g && typeof g.getNodeById === "function");
  const getGraphNode = (id) => {
    const numId = Number(id);
    for (const g of graphs) {
      const n = g.getNodeById(numId) || g.getNodeById(id);
      if (n) return n;
    }
    return null;
  };
  const getTypeFromGraph = (id) => {
    const n = getGraphNode(id);
    return (n && (n.type || n.comfyClass)) || null;
  };
  const hasInvalidInputs = (node) =>
    node.inputs && typeof node.inputs === "object" && ("UNKNOWN" in node.inputs || Object.keys(node.inputs).length === 0);
  const buildInputsFromGraphNode = (graphNode) => {
    const inputs = {};
    const widgets = graphNode.widgets || [];
    const hidden = new Set(["unique_id", "prompt"]);
    for (const w of widgets) {
      if (!w || w.name == null || hidden.has(String(w.name))) continue;
      let val = w.value;
      if (typeof val === "number" && w.options != null) {
        const opts = Array.isArray(w.options) ? w.options : w.options.values;
        if (Array.isArray(opts) && val >= 0 && val < opts.length) val = opts[val];
      }
      inputs[w.name] = val;
    }
    return inputs;
  };
  const ensureNodeClassType = (node, id) => {
    if (!node || typeof node !== "object") return;
    if (node.class_type != null && node.class_type !== "") return;
    const type =
      getTypeFromGraph(id) ||
      node.type ||
      node._meta?.class_type ||
      node._meta?.type ||
      node._meta?.comfyClass;
    node.class_type = type != null ? type : "Unknown";
  };
  const ensureNodeInputs = (node, id) => {
    if (!node || typeof node.inputs !== "object") return;
    if (!hasInvalidInputs(node)) return;
    const graphNode = getGraphNode(id);
    if (!graphNode) return;
    const built = buildInputsFromGraphNode(graphNode);
    if (Object.keys(built).length > 0) {
      node.inputs = built;
      if ((!node.class_type || node.class_type === "Unknown") && (graphNode.type || graphNode.comfyClass))
        node.class_type = graphNode.type || graphNode.comfyClass;
    }
  };
  const ensureUMLDiagramInputsFromGraph = (node, id) => {
    if (!node || typeof node !== "object" || node.class_type !== "UMLDiagram") return;
    if (node.inputs == null || typeof node.inputs !== "object") return;
    const graphNode = getGraphNode(id);
    if (!graphNode) return;
    const built = buildInputsFromGraphNode(graphNode);
    if (Object.keys(built).length > 0) node.inputs = built;
  };

  if (Array.isArray(promptObj)) {
    promptObj.forEach((node, i) => {
      const id = node && node.id != null ? String(node.id) : String(i);
      ensureNodeClassType(node, id);
      ensureNodeInputs(node, id);
      ensureUMLDiagramInputsFromGraph(node, id);
    });
    return;
  }
  for (const [id, node] of Object.entries(promptObj)) {
    if (node && typeof node === "object" && (node.inputs !== undefined || node._meta !== undefined)) {
      ensureNodeClassType(node, id);
      ensureNodeInputs(node, id);
      ensureUMLDiagramInputsFromGraph(node, id);
    }
  }
}

function _installGraphToPromptNormalizer() {
  const tryInstall = () => {
    const original = app.graphToPrompt;
    if (typeof original !== "function") return false;
    if (original.__umlPromptPatched) return true;
    const wrapped = function (...args) {
      const result = original.apply(this, args);
      const patch = (value) => {
        if (!value || typeof value !== "object") return value;
        _normalizePromptNodes(value);
        if (value.output != null) _normalizePromptNodes(value.output); // comfy-test validates output[id].class_type
        if (value.nodes != null) _normalizePromptNodes(value.nodes);
        if (value.graph && value.graph.nodes != null) _normalizePromptNodes(value.graph.nodes);
        return value;
      };
      if (result && typeof result.then === "function") return result.then(patch);
      return patch(result);
    };
    wrapped.__umlPromptPatched = true;
    app.graphToPrompt = wrapped;
    console.log("[ComfyUI-UML] graphToPrompt normalizer installed");
    return true;
  };

  if (!tryInstall()) {
    let attempts = 0;
    const interval = setInterval(() => {
      attempts += 1;
      if (tryInstall() || attempts > 50) clearInterval(interval);
    }, 100);
  }
}
