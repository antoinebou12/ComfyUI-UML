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
    const bound = group.bound;
    if (Array.isArray(bound) && bound.length >= 4) {
      const nums = bound.slice(0, 4).map((v) => Number(v));
      if (nums.every(Number.isFinite)) continue;
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
  }
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

  const links = data.links;
  if (!Array.isArray(links) || _isLinksCorrupted(links)) {
    data.links = _rebuildLinks(nodes);
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
      let normalized = graphData;
      try {
        normalized = _normalizeWorkflowData(graphData);
      } catch (e) {
        console.warn("[ComfyUI-UML] Workflow normalize failed:", e);
      }
      return original.call(this, normalized, ...rest);
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
  },
});
