/**
 * Viewer shell: parses url/embed/format, fetches diagram, loads view module by format,
 * and runs pan/zoom, crop, toolbar, save. Supports svg, png, txt, base64, iframe, markdown.
 */
import { getViewDescriptor } from "./views/view_manifest.js";
import { formatFromUrl } from "./viewerUrlUtils.mjs";

/** Return a clean error message string from any thrown value. */
function errMsg(e) {
  return (e && e.message) ? e.message : String(e);
}

function getUrlParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

const isEmbed = getUrlParam("embed") === "1" || window.self !== window.top;
if (isEmbed) {
  document.getElementById("toolbar").classList.add("toolbar-embed");
}

const content = document.getElementById("content");
const message = document.getElementById("message");
const zoomOutBtn = document.getElementById("zoom-out");
const zoomFitBtn = document.getElementById("zoom-fit");
const zoom100Btn = document.getElementById("zoom-100");
const zoomInBtn = document.getElementById("zoom-in");
const zoomLabel = document.getElementById("zoom-label");
const downloadBtn = document.getElementById("download");
const saveComfyBtn = document.getElementById("save-comfy");
const copyLinkBtn = document.getElementById("copy-link");
const saveStatus = document.getElementById("save-status");
const cropBtn = document.getElementById("crop-btn");
const clearSelectionBtn = document.getElementById("clear-selection");
const saveCropLocalBtn = document.getElementById("save-crop-local");
const saveCropComfyBtn = document.getElementById("save-crop-comfy");
const zoomToSelectionBtn = document.getElementById("zoom-to-selection");
const copyImageBtn = document.getElementById("copy-image");
const cropOverlay = document.getElementById("crop-overlay");
const urlInput = document.getElementById("url-input");
const urlViewBtn = document.getElementById("url-view-btn");

let krokiUrl = "";
let currentBlob = null;
let currentFormat = "svg";
let scale = 1;
let panX = 0;
let panY = 0;
const minScale = 0.25;
const maxScale = 4;
const step = 0.25;

let isPanning = false;
let startClientX = 0;
let startClientY = 0;
let startPanX = 0;
let startPanY = 0;

let isCropMode = false;
let selectionRect = null;
let isSelecting = false;
let selectStartX = 0;
let selectStartY = 0;
let selectEndX = 0;
let selectEndY = 0;

function getPanZoomLayer() {
  return content.querySelector(".pan-zoom-layer");
}

function getViewportElement() {
  const layer = getPanZoomLayer();
  return layer ? layer.querySelector(".viewport") : null;
}

function getContentBounds() {
  const viewport = getViewportElement();
  if (!viewport) return null;
  const svg = viewport.querySelector("svg");
  const img = viewport.querySelector("img");
  if (svg) {
    const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width !== undefined
      ? svg.viewBox.baseVal
      : svg.getBBox();
    return { left: vb.x, top: vb.y, width: vb.width, height: vb.height };
  }
  if (img && img.naturalWidth) {
    return { left: 0, top: 0, width: img.naturalWidth, height: img.naturalHeight };
  }
  return null;
}

function clientToContent(clientX, clientY) {
  const viewport = getViewportElement();
  const bounds = getContentBounds();
  if (!viewport || !bounds) return null;
  const r = viewport.getBoundingClientRect();
  const x = bounds.left + (clientX - r.left) / r.width * bounds.width;
  const y = bounds.top + (clientY - r.top) / r.height * bounds.height;
  return { x: x, y: y };
}

function contentToClient(contentX, contentY) {
  const viewport = getViewportElement();
  const bounds = getContentBounds();
  if (!viewport || !bounds) return null;
  const r = viewport.getBoundingClientRect();
  const x = r.left + (contentX - bounds.left) / bounds.width * r.width;
  const y = r.top + (contentY - bounds.top) / bounds.height * r.height;
  return { x: x, y: y };
}

function applyTransform() {
  const layer = getPanZoomLayer();
  if (layer) {
    layer.style.transform = "translate(" + panX + "px, " + panY + "px) scale(" + scale + ")";
  }
  if (zoomLabel) zoomLabel.textContent = Math.round(scale * 100) + "%";
}

function updateCropOverlay() {
  if (!selectionRect || !cropOverlay) return;
  const container = document.querySelector(".container");
  if (!container) return;
  const cr = container.getBoundingClientRect();
  const p1 = contentToClient(selectionRect.x, selectionRect.y);
  const p2 = contentToClient(selectionRect.x + selectionRect.w, selectionRect.y + selectionRect.h);
  if (!p1 || !p2) return;
  const left = Math.min(p1.x, p2.x) - cr.left;
  const top = Math.min(p1.y, p2.y) - cr.top;
  const w = Math.abs(p2.x - p1.x);
  const h = Math.abs(p2.y - p1.y);
  cropOverlay.style.left = left + "px";
  cropOverlay.style.top = top + "px";
  cropOverlay.style.width = w + "px";
  cropOverlay.style.height = h + "px";
  cropOverlay.style.display = w > 1 && h > 1 ? "block" : "none";
}

function updateCropUI() {
  const hasSelection = selectionRect && selectionRect.w > 0 && selectionRect.h > 0;
  cropBtn.classList.toggle("active", isCropMode);
  clearSelectionBtn.style.display = hasSelection ? "" : "none";
  saveCropLocalBtn.style.display = hasSelection ? "" : "none";
  saveCropComfyBtn.style.display = hasSelection ? "" : "none";
  zoomToSelectionBtn.style.display = hasSelection ? "" : "none";
  if (hasSelection) updateCropOverlay();
  else cropOverlay.style.display = "none";
  const container = document.querySelector(".container");
  if (container) container.classList.toggle("crop-mode", isCropMode);
}

function setupPanZoom() {
  const container = document.querySelector(".container");
  if (!container) return;

  container.addEventListener("wheel", function (e) {
    const layer = getPanZoomLayer();
    if (!layer) return;
    e.preventDefault();
    const layerRect = layer.getBoundingClientRect();
    const scaleFactor = 1 - e.deltaY * 0.002;
    const scaleNew = Math.max(minScale, Math.min(maxScale, scale * scaleFactor));
    if (scaleNew === scale) return;
    const cx = e.clientX - layerRect.left;
    const cy = e.clientY - layerRect.top;
    panX = cx - (cx - panX) * (scaleNew / scale);
    panY = cy - (cy - panY) * (scaleNew / scale);
    scale = scaleNew;
    applyTransform();
  }, { passive: false });

  container.addEventListener("pointerdown", function (e) {
    const layer = getPanZoomLayer();
    if (!layer || e.button !== 0) return;
    if (!isEmbed && isCropMode) {
      const pt = clientToContent(e.clientX, e.clientY);
      if (pt) {
        isSelecting = true;
        selectStartX = pt.x;
        selectStartY = pt.y;
        selectEndX = pt.x;
        selectEndY = pt.y;
        selectionRect = { x: pt.x, y: pt.y, w: 0, h: 0 };
        updateCropOverlay();
        e.currentTarget.setPointerCapture(e.pointerId);
      }
      return;
    }
    isPanning = true;
    startClientX = e.clientX;
    startClientY = e.clientY;
    startPanX = panX;
    startPanY = panY;
    container.classList.add("panning");
    e.currentTarget.setPointerCapture(e.pointerId);
  });

  container.addEventListener("pointermove", function (e) {
    if (isSelecting) {
      const pt = clientToContent(e.clientX, e.clientY);
      if (pt) {
        selectEndX = pt.x;
        selectEndY = pt.y;
        const x = Math.min(selectStartX, selectEndX);
        const y = Math.min(selectStartY, selectEndY);
        selectionRect = {
          x: x,
          y: y,
          w: Math.abs(selectEndX - selectStartX),
          h: Math.abs(selectEndY - selectStartY)
        };
        updateCropOverlay();
      }
      e.preventDefault();
      return;
    }
    if (!isPanning) return;
    panX = startPanX + (e.clientX - startClientX);
    panY = startPanY + (e.clientY - startClientY);
    applyTransform();
    e.preventDefault();
  });

  container.addEventListener("pointerup", function (e) {
    if (e.button !== 0) return;
    if (isSelecting) {
      isSelecting = false;
      e.currentTarget.releasePointerCapture(e.pointerId);
      if (selectionRect && selectionRect.w < 2 && selectionRect.h < 2) selectionRect = null;
      updateCropUI();
      return;
    }
    isPanning = false;
    container.classList.remove("panning");
    e.currentTarget.releasePointerCapture(e.pointerId);
  });

  container.addEventListener("pointercancel", function () {
    isSelecting = false;
    isPanning = false;
    container.classList.remove("panning");
    updateCropUI();
  });
}

setupPanZoom();

function showMessage(text, isError) {
  message.textContent = text;
  message.className = "message" + (isError ? " error" : "");
  message.style.display = "block";
  document.querySelector(".container")?.classList.remove("has-diagram");
}

function hideMessage() {
  message.style.display = "none";
}

function setZoom(s) {
  scale = Math.max(minScale, Math.min(maxScale, s));
  panX = 0;
  panY = 0;
  applyTransform();
}

function fitToView() {
  const container = document.querySelector(".container");
  const layer = getPanZoomLayer();
  if (!layer || !container) return;
  const viewport = layer.querySelector(".viewport");
  const el = viewport ? viewport.querySelector("img, svg") : null;
  if (!el) return;
  const cr = container.getBoundingClientRect();
  const w = el.offsetWidth || el.getBoundingClientRect().width;
  const h = el.offsetHeight || el.getBoundingClientRect().height;
  if (w <= 0 || h <= 0) return;
  const padding = isEmbed ? 32 : 40;
  const sx = (cr.width - padding) / w;
  const sy = (cr.height - padding) / h;
  scale = Math.min(sx, sy, 1);
  panX = 0;
  panY = 0;
  applyTransform();
}

function showSaveStatus(text, isError) {
  saveStatus.textContent = text;
  saveStatus.className = "save-status " + (isError ? "error" : "success");
  saveStatus.style.display = "block";
  clearTimeout(saveStatus._hide);
  saveStatus._hide = setTimeout(function () { saveStatus.style.display = "none"; }, 4000);
}

function saveBlobToComfyUI(blob, filename, buttonEl, successMessage) {
  if (!blob) return;
  buttonEl.disabled = true;
  const formData = new FormData();
  formData.append("file", blob, filename);
  fetch("/comfyui-uml/save", { method: "POST", body: formData })
    .then(function (res) {
      return res.text().then(function (text) {
        let data;
        const trimmed = (text || "").trim();
        if (trimmed === "") {
          data = { error: "Empty response" };
        } else {
          try {
            data = JSON.parse(trimmed);
          } catch (e) {
            data = { error: "Invalid response from server" };
          }
        }
        return { ok: res.ok, data: data };
      });
    })
    .then(function (result) {
      buttonEl.disabled = false;
      if (result.ok) {
        showSaveStatus(successMessage + (result.data.filename || ""), false);
      } else {
        showSaveStatus(result.data.error || "Save failed", true);
      }
    })
    .catch(function (err) {
      buttonEl.disabled = false;
      showSaveStatus(err.message || "Save to ComfyUI only works when the viewer is opened from ComfyUI", true);
    });
}

zoomOutBtn.addEventListener("click", function () { setZoom(scale - step); });
zoomInBtn.addEventListener("click", function () { setZoom(scale + step); });
zoom100Btn.addEventListener("click", function () { setZoom(1); });
zoomFitBtn.addEventListener("click", fitToView);

function getDownloadExtension() {
  if (currentFormat === "markdown") return "md";
  if (currentFormat === "jpeg") return "jpg";
  return currentFormat;
}

downloadBtn.addEventListener("click", function () {
  if (!currentBlob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(currentBlob);
  a.download = "diagram." + getDownloadExtension();
  a.click();
  URL.revokeObjectURL(a.href);
});

saveComfyBtn.addEventListener("click", function () {
  if (!currentBlob) return;
  saveBlobToComfyUI(
    currentBlob,
    "diagram_" + Date.now() + "." + getDownloadExtension(),
    saveComfyBtn,
    "Saved to output/uml/"
  );
});

copyLinkBtn.addEventListener("click", function () {
  if (!krokiUrl) return;
  navigator.clipboard.writeText(krokiUrl).then(function () {
    const t = copyLinkBtn.textContent;
    copyLinkBtn.textContent = "Copied!";
    setTimeout(function () { copyLinkBtn.textContent = t; }, 1500);
  });
});

cropBtn.addEventListener("click", function () {
  if (!getPanZoomLayer()) return;
  isCropMode = !isCropMode;
  if (!isCropMode) {
    selectionRect = null;
  }
  updateCropUI();
});

clearSelectionBtn.addEventListener("click", function () {
  selectionRect = null;
  isCropMode = false;
  updateCropUI();
});

function getPngBlobForClipboard(cb) {
  const viewport = getViewportElement();
  if (!viewport) { cb(null); return; }
  const svg = viewport.querySelector("svg");
  const img = viewport.querySelector("img");
  function drawToCanvas(w, h, draw) {
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.floor(w));
    c.height = Math.max(1, Math.floor(h));
    const ctx = c.getContext("2d");
    if (!ctx) { cb(null); return; }
    draw(ctx, c);
    c.toBlob(function (blob) { cb(blob || null); }, "image/png");
  }
  if (selectionRect && selectionRect.w > 0 && selectionRect.h > 0) {
    if (img && img.complete && img.naturalWidth) {
      drawToCanvas(selectionRect.w, selectionRect.h, function (ctx, c) {
        ctx.drawImage(img, selectionRect.x, selectionRect.y, selectionRect.w, selectionRect.h, 0, 0, c.width, c.height);
      });
      return;
    }
    if (svg) {
      const clone = svg.cloneNode(true);
      const r = selectionRect;
      clone.setAttribute("viewBox", r.x + " " + r.y + " " + r.w + " " + r.h);
      clone.setAttribute("width", String(r.w));
      clone.setAttribute("height", String(r.h));
      const s = new XMLSerializer().serializeToString(clone);
      const url = URL.createObjectURL(new Blob([s], { type: "image/svg+xml" }));
      const im = new Image();
      im.onload = function () {
        drawToCanvas(r.w, r.h, function (ctx, c) {
          ctx.drawImage(im, 0, 0, c.width, c.height);
        });
        URL.revokeObjectURL(url);
      };
      im.onerror = function () { URL.revokeObjectURL(url); cb(null); };
      im.src = url;
      return;
    }
  }
  if (img && img.complete) {
    const w = img.naturalWidth || img.offsetWidth;
    const h = img.naturalHeight || img.offsetHeight;
    if (currentBlob && currentBlob.type === "image/png") {
      cb(currentBlob);
      return;
    }
    drawToCanvas(w, h, function (ctx, c) {
      ctx.drawImage(img, 0, 0, c.width, c.height);
    });
    return;
  }
  if (svg) {
    const w = svg.viewBox && svg.viewBox.baseVal.width ? svg.viewBox.baseVal.width : svg.getBBox().width;
    const h = svg.viewBox && svg.viewBox.baseVal.height ? svg.viewBox.baseVal.height : svg.getBBox().height;
    const s = new XMLSerializer().serializeToString(svg);
    const url = URL.createObjectURL(new Blob([s], { type: "image/svg+xml" }));
    const im = new Image();
    im.onload = function () {
      drawToCanvas(w, h, function (ctx, c) {
        ctx.drawImage(im, 0, 0, c.width, c.height);
      });
      URL.revokeObjectURL(url);
    };
    im.onerror = function () { URL.revokeObjectURL(url); cb(null); };
    im.src = url;
    return;
  }
  cb(null);
}

copyImageBtn.addEventListener("click", function () {
  if (!getPanZoomLayer()) return;
  getPngBlobForClipboard(function (blob) {
    if (!blob) {
      showSaveStatus("Copy not supported or failed", true);
      return;
    }
    if (!navigator.clipboard || !navigator.clipboard.write) {
      showSaveStatus("Copy not supported in this browser", true);
      return;
    }
    navigator.clipboard.write([new ClipboardItem({ "image/png": blob })])
      .then(function () {
        showSaveStatus("Copied to clipboard", false);
      })
      .catch(function () {
        showSaveStatus("Paste from the downloaded image if copy failed", true);
      });
  });
});

zoomToSelectionBtn.addEventListener("click", function () {
  if (!selectionRect || !selectionRect.w || !selectionRect.h) return;
  const container = document.querySelector(".container");
  const layer = getPanZoomLayer();
  if (!container || !layer) return;
  const cr = container.getBoundingClientRect();
  const padding = 40;
  const sx = (cr.width - padding) / selectionRect.w;
  const sy = (cr.height - padding) / selectionRect.h;
  scale = Math.min(sx, sy, maxScale);
  scale = Math.max(minScale, scale);
  const centerX = selectionRect.x + selectionRect.w / 2;
  const centerY = selectionRect.y + selectionRect.h / 2;
  applyTransform();
  const contentRect = content.getBoundingClientRect();
  const containerCenterX = cr.left + cr.width / 2;
  const containerCenterY = cr.top + cr.height / 2;
  panX = containerCenterX - contentRect.left - (layer.offsetLeft || 0) - centerX * scale;
  panY = containerCenterY - contentRect.top - (layer.offsetTop || 0) - centerY * scale;
  applyTransform();
  updateCropOverlay();
});

function getCroppedBlob(cb) {
  if (!selectionRect || selectionRect.w <= 0 || selectionRect.h <= 0) { cb(null); return; }
  const viewport = getViewportElement();
  if (!viewport) { cb(null); return; }
  const svg = viewport.querySelector("svg");
  const img = viewport.querySelector("img");
  if (svg) {
    const clone = svg.cloneNode(true);
    const r = selectionRect;
    clone.setAttribute("viewBox", r.x + " " + r.y + " " + r.w + " " + r.h);
    clone.setAttribute("width", String(r.w));
    clone.setAttribute("height", String(r.h));
    const s = new XMLSerializer().serializeToString(clone);
    cb(new Blob([s], { type: "image/svg+xml" }), "svg");
    return;
  }
  if (img && img.complete && img.naturalWidth) {
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.floor(selectionRect.w));
    c.height = Math.max(1, Math.floor(selectionRect.h));
    const ctx = c.getContext("2d");
    if (!ctx) { cb(null); return; }
    ctx.drawImage(img, selectionRect.x, selectionRect.y, selectionRect.w, selectionRect.h, 0, 0, c.width, c.height);
    c.toBlob(function (blob) { cb(blob || null, "png"); }, "image/png");
    return;
  }
  cb(null);
}

saveCropLocalBtn.addEventListener("click", function () {
  getCroppedBlob(function (blob, format) {
    if (!blob) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "diagram_crop_" + Date.now() + "." + (format || "png");
    a.click();
    URL.revokeObjectURL(a.href);
    showSaveStatus("Cropped region saved locally", false);
  });
});

saveCropComfyBtn.addEventListener("click", function () {
  getCroppedBlob(function (blob, format) {
    if (!blob) return;
    saveBlobToComfyUI(
      blob,
      "uml_crop_" + Date.now() + "." + (format || "png"),
      saveCropComfyBtn,
      "Saved crop to output/uml/"
    );
  });
});

function enableToolbarAfterRender(isImageFormat, isSaveableFile) {
  if (isSaveableFile === undefined) isSaveableFile = false;
  document.querySelector(".container")?.classList.add("has-diagram");
  scale = 1;
  panX = 0;
  panY = 0;
  applyTransform();
  if (!isEmbed) {
    const canSave = isImageFormat || isSaveableFile || currentBlob != null;
    downloadBtn.disabled = !canSave;
    saveComfyBtn.disabled = !canSave;
    copyLinkBtn.disabled = !krokiUrl;
    cropBtn.disabled = !isImageFormat;
    copyImageBtn.disabled = !isImageFormat;
  }
  if (isEmbed) requestAnimationFrame(fitToView);
}

function decodeDataUrlPayload(header, payload) {
  const lower = header.toLowerCase();
  if (lower.includes("base64")) {
    try {
      const binary = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return { bytes };
    } catch (e) {
      return null;
    }
  }
  try {
    return { text: decodeURIComponent(payload) };
  } catch (e) {
    return { text: payload };
  }
}

function parseDataUrl(url) {
  if (!url || !url.startsWith("data:")) return null;
  const comma = url.indexOf(",");
  if (comma === -1) return { error: "invalid" };
  const header = url.slice(0, comma).toLowerCase();
  const payload = url.slice(comma + 1);
  const decoded = decodeDataUrlPayload(url.slice(0, comma), payload);
  if (!decoded) return { error: "invalid_base64" };
  if (header.includes("image/svg+xml")) {
    const svgText = decoded.bytes ? new TextDecoder().decode(decoded.bytes) : (decoded.text || "");
    return {
      format: "svg",
      data: svgText,
      blob: new Blob([svgText], { type: "image/svg+xml" }),
      clearKrokiUrl: true,
    };
  }
  if (header.includes("image/png") || header.includes("image/jpeg")) {
    if (!decoded.bytes) return { error: "unsupported" };
    const mime = header.includes("image/png") ? "image/png" : "image/jpeg";
    const blob = new Blob([decoded.bytes], { type: mime });
    return {
      format: mime === "image/png" ? "png" : "jpeg",
      data: blob,
      blob,
      clearKrokiUrl: false,
    };
  }
  if (header.includes("text/plain")) {
    const text = decoded.bytes ? new TextDecoder().decode(decoded.bytes) : (decoded.text || "");
    return { format: "txt", data: text, clearKrokiUrl: false };
  }
  if (header.includes("text/markdown")) {
    const md = decoded.bytes ? new TextDecoder().decode(decoded.bytes) : (decoded.text || "");
    return { format: "markdown", data: md, clearKrokiUrl: false };
  }
  return { error: "unsupported" };
}

async function renderWithView(contentEl, format, data, options) {
  const opts = options || {};
  const descriptor = getViewDescriptor(format);
  const view = await descriptor.load();
  const renderResult = view.render(contentEl, data);
  if (renderResult && typeof renderResult.then === "function") await renderResult;
  if (opts.blob != null) currentBlob = opts.blob;
  else if (format === "svg" && typeof data === "string") currentBlob = new Blob([data], { type: "image/svg+xml" });
  else if ((format === "png" || format === "jpeg") && data instanceof Blob) currentBlob = data;
  else if (format === "txt" && typeof data === "string") currentBlob = new Blob([data], { type: "text/plain" });
  else if (format === "markdown" && typeof data === "string") currentBlob = new Blob([data], { type: "text/markdown" });
  else if (format === "base64" && typeof data === "string") currentBlob = new Blob([data], { type: "application/octet-stream" });
  if (opts.clearKrokiUrl) krokiUrl = "";
  enableToolbarAfterRender(opts.isImageFormat === true, opts.isSaveableFile === true);
}

async function loadDiagram(url) {
  const formatFromQuery = getUrlParam("format");
  krokiUrl = url;
  currentBlob = null;
  selectionRect = null;
  isCropMode = false;
  downloadBtn.disabled = true;
  saveComfyBtn.disabled = true;
  copyLinkBtn.disabled = true;
  cropBtn.disabled = true;
  copyImageBtn.disabled = true;
  updateCropUI();

  if (url.startsWith("data:")) {
    const parsed = parseDataUrl(url);
    if (parsed && parsed.error) {
      if (parsed.error === "invalid") showMessage("Invalid data URL.", true);
      else if (parsed.error === "invalid_base64") showMessage("Invalid base64 in data URL.", true);
      else showMessage("Data URL must be image/svg+xml, image/png, text/plain, or text/markdown.", true);
      return;
    }
    if (!parsed) {
      showMessage("Data URL must be image/svg+xml, image/png, text/plain, or text/markdown.", true);
      return;
    }
    currentFormat = parsed.format;
    hideMessage();
    await renderWithView(content, parsed.format, parsed.data, {
      isImageFormat: parsed.format === "svg" || parsed.format === "png" || parsed.format === "jpeg",
      blob: parsed.blob,
      clearKrokiUrl: parsed.clearKrokiUrl,
    });
    return;
  }

  const formatParam = formatFromQuery ? formatFromQuery.toLowerCase().trim() : "";

  if (
    formatParam === "svg" &&
    !url.startsWith("data:") &&
    !url.startsWith("http://") &&
    !url.startsWith("https://")
  ) {
    const trimmed = url.trim();
    if (trimmed.toLowerCase().startsWith("<?xml") || trimmed.toLowerCase().startsWith("<svg")) {
      currentFormat = "svg";
      hideMessage();
      await renderWithView(content, "svg", trimmed, {
        isImageFormat: true,
        blob: new Blob([trimmed], { type: "image/svg+xml" }),
        clearKrokiUrl: true,
      });
      return;
    }
  }

  if (formatParam === "iframe") {
    currentFormat = "iframe";
    hideMessage();
    await renderWithView(content, "iframe", url, { isImageFormat: false });
    return;
  }

  if (formatParam === "markdown") {
    let markdownContent = getUrlParam("content");
    if (markdownContent != null) {
      try {
        markdownContent = decodeURIComponent(markdownContent);
      } catch (_) {}
    }
    if (!markdownContent && (url.startsWith("http:") || url.startsWith("https:"))) {
      showMessage("Loading…", false);
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("HTTP " + res.status);
        markdownContent = await res.text();
      } catch (e) {
        showMessage("Failed to load markdown: " + e.message, true);
        return;
      }
    }
    if (markdownContent != null && markdownContent !== "") {
      currentFormat = "markdown";
      hideMessage();
      await renderWithView(content, "markdown", markdownContent, { isImageFormat: false });
      return;
    }
  }

  currentFormat = formatParam || formatFromUrl(url);
  showMessage("Loading…", false);

  let res;
  try {
    res = await fetch(url);
  } catch (directErr) {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      try {
        res = await fetch("/comfyui-uml/proxy?url=" + encodeURIComponent(url));
      } catch (proxyErr) {
        showMessage("Failed to load diagram: " + errMsg(directErr) + " (proxy also failed: " + errMsg(proxyErr) + ")", true);
        return;
      }
    } else {
      showMessage("Failed to load diagram: " + errMsg(directErr), true);
      return;
    }
  }
  if (!res.ok) {
    showMessage("Failed to load diagram: HTTP " + res.status, true);
    return;
  }

  try {
    if (currentFormat === "txt") {
      const text = await res.text();
      hideMessage();
      await renderWithView(content, "txt", text, { isImageFormat: false });
      return;
    }

    if (currentFormat === "base64") {
      const b64Text = await res.text();
      let bytes;
      try {
        const binary = atob(b64Text.trim().replace(/-/g, "+").replace(/_/g, "/"));
        bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      } catch (e) {
        showMessage("Invalid base64 response.", true);
        return;
      }
      hideMessage();
      // Detect image type from magic bytes; pass blob via opts so renderWithView sets currentBlob
      const isPng = bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e;
      const isSvg = (bytes.length >= 5 && String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4]) === "<?xml")
        || (bytes.length >= 4 && bytes[0] === 0x3c && bytes[1] === 0x73 && bytes[2] === 0x76 && bytes[3] === 0x67);
      if (isPng) {
        const blob = new Blob([bytes], { type: "image/png" });
        await renderWithView(content, "png", blob, { isImageFormat: true, blob });
        return;
      }
      if (isSvg) {
        const svgBlob = new Blob([bytes], { type: "image/svg+xml" });
        await renderWithView(content, "svg", new TextDecoder().decode(bytes), { isImageFormat: true, blob: svgBlob });
        return;
      }
      await renderWithView(content, "base64", new TextDecoder().decode(bytes), { isImageFormat: false });
      return;
    }

    const data = currentFormat === "svg" ? await res.text() : await res.blob();
    hideMessage();
    await renderWithView(content, currentFormat, data, {
      isImageFormat: currentFormat === "svg" || currentFormat === "png" || currentFormat === "jpeg",
      isSaveableFile: currentFormat === "pdf",
      blob: currentFormat === "svg" ? new Blob([data], { type: "image/svg+xml" }) : data,
    });
  } catch (err) {
    const msg = errMsg(err);
    if (msg && msg.includes("Invalid SVG")) {
      showMessage("Diagram could not be displayed.", true);
    } else {
      showMessage("Failed to render diagram: " + msg, true);
    }
  }
}

const url = getUrlParam("url");
if (url) {
  showMessage("Loading…", false);
  (async function () {
    try {
      const decoded = decodeURIComponent(url);
      await loadDiagram(decoded);
    } catch (e) {
      await loadDiagram(url);
    }
  })().catch(function (err) {
    showMessage("Failed to load: " + errMsg(err), true);
  });
}

function loadFromUrlInput() {
  const raw = urlInput && urlInput.value ? urlInput.value.trim() : "";
  if (!raw) return;
  const params = new URLSearchParams(window.location.search);
  params.set("url", raw);
  const newSearch = "?" + params.toString();
  if (window.location.search !== newSearch) {
    history.replaceState(null, "", window.location.pathname + newSearch + (window.location.hash || ""));
  }
  showMessage("Loading…", false);
  loadDiagram(raw).catch(function (err) {
    showMessage("Failed to load: " + errMsg(err), true);
  });
}

if (urlViewBtn && urlInput) {
  urlViewBtn.addEventListener("click", loadFromUrlInput);
  urlInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") loadFromUrlInput();
  });
  if (url) {
    try {
      urlInput.value = decodeURIComponent(url);
    } catch (_) {
      urlInput.value = url;
    }
  }
}

