/**
 * Dynamic Widget & Input Slot Visibility for ComfyUI
 * From comfy-dynamic-widgets; loads mappings.json from same directory.
 * mappings.json is generated at runtime by the Python package comfy_dynamic_widgets when installed (see __init__.py).
 * Version 2 format: visible_when with multi-selector AND logic.
 */
import { app } from "../../../../scripts/app.js";

console.log("[DynamicWidgets] Loading extension...");

let MAPPINGS = null;

async function loadMappings() {
  const scriptUrl = new URL(import.meta.url);
  const baseDir = scriptUrl.pathname.substring(0, scriptUrl.pathname.lastIndexOf("/"));
  try {
    const response = await fetch(baseDir + "/mappings.json");
    if (response.ok) {
      const data = await response.json();
      MAPPINGS = data;
      const nodeCount = Object.keys(data.nodes || {}).length;
      console.log(`[DynamicWidgets] Loaded mappings v${data.version || 1} for ${nodeCount} nodes`);
      return true;
    }
  } catch (e) {
    console.warn("[DynamicWidgets] Could not load mappings.json:", e);
  }
  return false;
}

loadMappings();

function getNodeConfig(nodeClass) {
  if (!MAPPINGS || !MAPPINGS.nodes) return null;
  return MAPPINGS.nodes[nodeClass] || null;
}

function hideInputSlot(node, slotName) {
  if (!node.inputs) return false;
  const input = node.inputs.find((i) => i.name === slotName);
  if (!input) return false;
  input._dw_originalIndex = (node._dw_originalInputOrder && node._dw_originalInputOrder[slotName] != null)
    ? node._dw_originalInputOrder[slotName]
    : node.inputs.indexOf(input);
  input._dw_hidden = true;
  node.inputs.splice(node.inputs.indexOf(input), 1);
  if (!node._dw_hiddenInputs) node._dw_hiddenInputs = {};
  node._dw_hiddenInputs[slotName] = input;
  return true;
}

function showInputSlot(node, slotName) {
  if (!node._dw_hiddenInputs || !node._dw_hiddenInputs[slotName]) return false;
  const input = node._dw_hiddenInputs[slotName];
  if (!input._dw_hidden) return false;
  if (!node.inputs) node.inputs = [];
  const myOrigIdx = input._dw_originalIndex != null ? input._dw_originalIndex : node.inputs.length;
  let insertIndex = 0;
  for (const inp of node.inputs) {
    const origIdx = (node._dw_originalInputOrder && node._dw_originalInputOrder[inp.name] != null)
      ? node._dw_originalInputOrder[inp.name]
      : Infinity;
    if (origIdx < myOrigIdx) insertIndex++;
  }
  if (node.inputs.indexOf(input) === -1) {
    node.inputs.splice(insertIndex, 0, input);
  }
  input._dw_hidden = false;
  delete node._dw_hiddenInputs[slotName];
  return true;
}

function isInputSlot(node, name) {
  if (node.inputs && node.inputs.some((i) => i.name === name)) return true;
  if (node._dw_hiddenInputs && node._dw_hiddenInputs[name]) return true;
  return false;
}

function applyVisibility(node, name, shouldShow) {
  const widget = (node.widgets || []).find((w) => w.name === name);
  if (widget) {
    const wasHidden = widget.hidden;
    widget.hidden = !shouldShow;
    return wasHidden !== widget.hidden;
  }
  if (isInputSlot(node, name)) {
    if (shouldShow) return showInputSlot(node, name);
    return hideInputSlot(node, name);
  }
  return false;
}

function evaluateAllRules(node) {
  const nodeConfig = getNodeConfig(node.comfyClass);
  if (!nodeConfig || !nodeConfig.rules || !nodeConfig.selectors) return;
  const selectorValues = {};
  for (const selName of nodeConfig.selectors) {
    const w = (node.widgets || []).find((w) => w.name === selName);
    selectorValues[selName] = w ? String(w.value) : null;
  }
  let visibilityChanged = false;
  for (const [widgetName, conditions] of Object.entries(nodeConfig.rules)) {
    let shouldShow = true;
    for (const [selName, allowedValues] of Object.entries(conditions)) {
      const currentValue = selectorValues[selName];
      if (currentValue === null || !allowedValues.includes(currentValue)) {
        shouldShow = false;
        break;
      }
    }
    if (applyVisibility(node, widgetName, shouldShow)) visibilityChanged = true;
  }
  if (visibilityChanged) {
    node.setSize(node.computeSize());
    app.graph.setDirtyCanvas(true, true);
  }
}

function setupV2Selectors(node) {
  const nodeConfig = getNodeConfig(node.comfyClass);
  if (!nodeConfig || !nodeConfig.selectors) return;
  for (const selName of nodeConfig.selectors) {
    const widget = (node.widgets || []).find((w) => w.name === selName);
    if (!widget) continue;
    const originalCallback = widget.callback;
    widget.callback = function (value) {
      if (originalCallback) originalCallback.call(this, value);
      evaluateAllRules(node);
    };
  }
  setTimeout(() => evaluateAllRules(node), 50);
}

app.registerExtension({
  name: "Comfy.DynamicWidgets",
  nodeCreated(node) {
    const nodeConfig = getNodeConfig(node.comfyClass);
    if (!nodeConfig) return;
    const version = MAPPINGS?.version || 1;
    const isV2 = version >= 2 && nodeConfig.rules;
    const hasV1Selectors = !isV2 && nodeConfig.selectors && typeof nodeConfig.selectors === "object" && !Array.isArray(nodeConfig.selectors);
    const hasConnections = nodeConfig.connections && Object.keys(nodeConfig.connections).length > 0;
    if (!isV2 && !hasV1Selectors && !hasConnections) return;
    node._dw_hiddenInputs = {};
    node._dw_originalInputOrder = {};
    if (node.inputs) {
      for (let i = 0; i < node.inputs.length; i++) {
        node._dw_originalInputOrder[node.inputs[i].name] = i;
      }
    }
    if (isV2) setupV2Selectors(node);
    if (hasConnections) {
      for (const [inputName, config] of Object.entries(nodeConfig.connections)) {
        const { source_widget, contains } = config;
        const controlledItems = Object.keys(contains || {});
        if (controlledItems.length === 0) continue;
        let lastSourceValue = undefined;
        const getConnectedWidgetValue = (n, inName, wName) => {
          const inp = n.inputs?.find((i) => i.name === inName);
          if (!inp || !inp.link) return null;
          const link = app.graph.links[inp.link];
          if (!link) return null;
          const src = app.graph.getNodeById(link.origin_id);
          if (!src) return null;
          const w = src.widgets?.find((x) => x.name === wName);
          return w ? w.value : null;
        };
        const updateVisibility = () => {
          const sourceValue = getConnectedWidgetValue(node, inputName, source_widget);
          if (sourceValue === lastSourceValue) return;
          lastSourceValue = sourceValue;
          let visibilityChanged = false;
          for (const itemName of controlledItems) {
            const patterns = contains[itemName] || [];
            const shouldShow = sourceValue == null ? true : patterns.some((p) => String(sourceValue).toLowerCase().includes(String(p).toLowerCase()));
            if (applyVisibility(node, itemName, shouldShow)) visibilityChanged = true;
          }
          if (visibilityChanged) {
            node.setSize(node.computeSize());
            app.graph.setDirtyCanvas(true, true);
          }
        };
        const origOnConnectionsChange = node.onConnectionsChange;
        node.onConnectionsChange = function (type, index, connected, link_info) {
          if (origOnConnectionsChange) origOnConnectionsChange.apply(this, arguments);
          if (type === 1) setTimeout(updateVisibility, 100);
        };
        setTimeout(updateVisibility, 200);
        const pollInterval = setInterval(() => {
          if (!node.graph) {
            clearInterval(pollInterval);
            return;
          }
          updateVisibility();
        }, 2000);
        const origOnRemoved = node.onRemoved;
        node.onRemoved = function () {
          clearInterval(pollInterval);
          if (origOnRemoved) origOnRemoved.apply(this, arguments);
        };
      }
    }
  },
});

console.log("[DynamicWidgets] Extension registered");
