/**
 * Viewer shell: parses url/embed/format, fetches diagram, loads view module by format,
 * and runs pan/zoom, crop, toolbar, save. Supports svg, png, txt, base64, iframe, markdown.
 */
import { getViewDescriptor } from "./views/view_manifest.js";

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
    .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
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

downloadBtn.addEventListener("click", function () {
  if (!currentBlob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(currentBlob);
  a.download = "diagram." + currentFormat;
  a.click();
  URL.revokeObjectURL(a.href);
});

saveComfyBtn.addEventListener("click", function () {
  if (!currentBlob) return;
  saveBlobToComfyUI(
    currentBlob,
    "diagram_" + Date.now() + "." + currentFormat,
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
    const canSave = isImageFormat || isSaveableFile;
    downloadBtn.disabled = !canSave;
    saveComfyBtn.disabled = !canSave;
    copyLinkBtn.disabled = !krokiUrl;
    cropBtn.disabled = !isImageFormat;
    copyImageBtn.disabled = !isImageFormat;
  }
  if (isEmbed) requestAnimationFrame(fitToView);
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
    const comma = url.indexOf(",");
    if (comma === -1) {
      showMessage("Invalid data URL.", true);
      return;
    }
    const header = url.slice(0, comma).toLowerCase();
    const payload = url.slice(comma + 1);
    if (header.includes("image/svg+xml")) {
      currentFormat = "svg";
      let svgText = "";
      if (header.includes("base64")) {
        try {
          svgText = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
        } catch (e) {
          showMessage("Invalid base64 in data URL.", true);
          return;
        }
      } else {
        try {
          svgText = decodeURIComponent(payload);
        } catch (e) {
          svgText = payload;
        }
      }
      hideMessage();
      const descriptor = getViewDescriptor(currentFormat);
      const view = await descriptor.load();
      const renderResult = view.render(content, svgText);
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      currentBlob = new Blob([svgText], { type: "image/svg+xml" });
      krokiUrl = "";
      copyLinkBtn.disabled = true;
      enableToolbarAfterRender(true);
      return;
    }
    if (header.includes("image/png") || header.includes("image/jpeg")) {
      try {
        const binary = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const mime = header.includes("image/png") ? "image/png" : "image/jpeg";
        const blob = new Blob([bytes], { type: mime });
        currentFormat = mime === "image/png" ? "png" : "jpeg";
        hideMessage();
        const descriptor = getViewDescriptor(currentFormat);
        const view = await descriptor.load();
        const renderResult = view.render(content, blob);
        if (renderResult && typeof renderResult.then === "function") await renderResult;
        currentBlob = blob;
        enableToolbarAfterRender(true);
      } catch (e) {
        showMessage("Invalid base64 in data URL.", true);
      }
      return;
    }
    if (header.includes("text/plain")) {
      let text = "";
      if (header.includes("base64")) {
        try {
          text = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
        } catch (e) {
          showMessage("Invalid base64 in data URL.", true);
          return;
        }
      } else {
        try {
          text = decodeURIComponent(payload);
        } catch (e) {
          text = payload;
        }
      }
      currentFormat = "txt";
      hideMessage();
      const descriptor = getViewDescriptor("txt");
      const view = await descriptor.load();
      const renderResult = view.render(content, text);
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      enableToolbarAfterRender(false);
      return;
    }
    if (header.includes("text/markdown")) {
      let md = "";
      if (header.includes("base64")) {
        try {
          md = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
        } catch (e) {
          showMessage("Invalid base64 in data URL.", true);
          return;
        }
      } else {
        try {
          md = decodeURIComponent(payload);
        } catch (e) {
          md = payload;
        }
      }
      currentFormat = "markdown";
      hideMessage();
      const descriptor = getViewDescriptor("markdown");
      const view = await descriptor.load();
      const renderResult = view.render(content, md);
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      enableToolbarAfterRender(false);
      return;
    }
    showMessage("Data URL must be image/svg+xml, image/png, text/plain, or text/markdown.", true);
    return;
  }

  const formatParam = formatFromQuery ? formatFromQuery.toLowerCase().trim() : "";

  if (formatParam === "iframe") {
    currentFormat = "iframe";
    hideMessage();
    const descriptor = getViewDescriptor("iframe");
    const view = await descriptor.load();
    const renderResult = view.render(content, url);
    if (renderResult && typeof renderResult.then === "function") await renderResult;
    enableToolbarAfterRender(false);
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
      const descriptor = getViewDescriptor("markdown");
      const view = await descriptor.load();
      const renderResult = view.render(content, markdownContent);
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      enableToolbarAfterRender(false);
      return;
    }
  }

  currentFormat = formatParam || (url.indexOf("/svg/") !== -1 ? "svg" : "png");
  showMessage("Loading…", false);

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);

    if (currentFormat === "txt") {
      const text = await res.text();
      hideMessage();
      const descriptor = getViewDescriptor("txt");
      const view = await descriptor.load();
      const renderResult = view.render(content, text);
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      enableToolbarAfterRender(false);
      return;
    }

    if (currentFormat === "base64") {
      const b64Text = await res.text();
      hideMessage();
      let bytes;
      try {
        const binary = atob(b64Text.trim().replace(/-/g, "+").replace(/_/g, "/"));
        bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      } catch (e) {
        showMessage("Invalid base64 response.", true);
        return;
      }
      const isPng = bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e;
      const start = bytes.length >= 5 ? String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4]) : "";
      const isSvg = start === "<?xml" || (bytes.length >= 4 && bytes[0] === 0x3c && bytes[1] === 0x73 && bytes[2] === 0x76 && bytes[3] === 0x67);
      if (isPng) {
        const blob = new Blob([bytes], { type: "image/png" });
        currentBlob = blob;
        const descriptor = getViewDescriptor("png");
        const view = await descriptor.load();
        const renderResult = view.render(content, blob);
        if (renderResult && typeof renderResult.then === "function") await renderResult;
        enableToolbarAfterRender(true);
        return;
      }
      if (isSvg) {
        const svgText = new TextDecoder().decode(bytes);
        currentBlob = new Blob([bytes], { type: "image/svg+xml" });
        const descriptor = getViewDescriptor("svg");
        const view = await descriptor.load();
        const renderResult = view.render(content, svgText);
        if (renderResult && typeof renderResult.then === "function") await renderResult;
        enableToolbarAfterRender(true);
        return;
      }
      const descriptor = getViewDescriptor("base64");
      const view = await descriptor.load();
      const renderResult = view.render(content, new TextDecoder().decode(bytes));
      if (renderResult && typeof renderResult.then === "function") await renderResult;
      enableToolbarAfterRender(false);
      return;
    }

    const data = currentFormat === "svg" ? await res.text() : await res.blob();
    hideMessage();
    const descriptor = getViewDescriptor(currentFormat);
    const view = await descriptor.load();
    const renderResult = view.render(content, data);
    if (renderResult && typeof renderResult.then === "function") await renderResult;
    if (currentFormat === "svg") {
      currentBlob = new Blob([data], { type: "image/svg+xml" });
    } else {
      currentBlob = data;
    }
    const isImage = currentFormat === "svg" || currentFormat === "png" || currentFormat === "jpeg";
    enableToolbarAfterRender(isImage, currentFormat === "pdf");
  } catch (err) {
    showMessage("Failed to load diagram: " + err.message + ". If the Kroki URL is from another origin, try opening it in a new tab.", true);
  }
}

const url = getUrlParam("url");
if (url) {
  (async function () {
    try {
      const decoded = decodeURIComponent(url);
      await loadDiagram(decoded);
    } catch (e) {
      await loadDiagram(url);
    }
  })();
}
