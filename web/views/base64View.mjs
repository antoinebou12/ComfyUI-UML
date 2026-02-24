/**
 * Base64 view: decodes base64 string and shows as image (PNG/SVG) or text fallback.
 * Used when format is "base64" and shell passes decoded blob or raw string.
 * For image blobs the shell may call png/svg view instead; this view handles
 * string (base64 or decoded text) and displays image when possible or text.
 */

/** Append SVG text to viewport: parse and append SVG element or pre fallback. */
function _appendSvgOrFallback(viewport, svgText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgText, "image/svg+xml");
  const svg = doc.documentElement;
  if (svg && svg.tagName && svg.tagName.toLowerCase() === "svg") {
    viewport.appendChild(svg);
  } else {
    const pre = document.createElement("pre");
    pre.style.cssText =
      "margin:0; padding:16px; white-space:pre-wrap; color:var(--comfy-text,#AAA); font-size:13px;";
    pre.textContent = svgText;
    viewport.appendChild(pre);
  }
}

/** Render SVG blob into viewport (async). */
function _renderSvgBlobToViewport(viewport, blob) {
  return blob.text().then((svgText) => _appendSvgOrFallback(viewport, svgText));
}

/** Create a viewport+layer wrapper and attach to container, returning the viewport element. */
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
  if (!container) return Promise.resolve();

  const viewport = _buildContainer(container);

  if (data instanceof Blob) {
    if (data.type === "image/svg+xml") {
      return _renderSvgBlobToViewport(viewport, data);
    }
    const img = document.createElement("img");
    img.alt = "Diagram";
    img.src = URL.createObjectURL(data);
    viewport.appendChild(img);
    return new Promise((resolve) => {
      img.onload = () => resolve();
      img.onerror = () => resolve();
    });
  }

  if (typeof data === "string") {
    const trimmed = data.trim();
    const looksLikeBase64 = /^[A-Za-z0-9+/=_-]+$/.test(trimmed) && trimmed.length >= 4;
    let decoded = "";
    let blob = null;

    if (looksLikeBase64) {
      try {
        const binary = atob(trimmed.replace(/-/g, "+").replace(/_/g, "/"));
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        if (bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e) {
          blob = new Blob([bytes], { type: "image/png" });
        } else if (
          bytes.length >= 5 &&
          (String.fromCharCode(...bytes.slice(0, 5)) === "<?xml" ||
            (bytes[0] === 0x3c && bytes[1] === 0x73 && bytes[2] === 0x76))
        ) {
          decoded = new TextDecoder().decode(bytes);
          if (decoded.trim().startsWith("<?xml") || decoded.trim().startsWith("<svg")) {
            blob = new Blob([bytes], { type: "image/svg+xml" });
          }
        }
        if (!blob) decoded = new TextDecoder().decode(bytes);
      } catch {
        decoded = data;
      }
    } else {
      decoded = data;
    }

    if (blob) {
      if (blob.type === "image/svg+xml") {
        return _renderSvgBlobToViewport(viewport, blob);
      }
      const img = document.createElement("img");
      img.alt = "Diagram";
      img.src = URL.createObjectURL(blob);
      viewport.appendChild(img);
      return new Promise((resolve) => {
        img.onload = () => resolve();
        img.onerror = () => resolve();
      });
    }

    const pre = document.createElement("pre");
    pre.style.cssText =
      "margin:0; padding:16px; white-space:pre-wrap; word-break:break-word; " +
      "color:var(--comfy-text,#AAA); font-family:monospace; font-size:13px; overflow:auto;";
    pre.textContent = decoded || "(empty or invalid base64)";
    viewport.appendChild(pre);
  }

  return Promise.resolve();
}
