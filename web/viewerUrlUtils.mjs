/**
 * Shared URL/format utilities for the diagram viewer.
 * Single source of truth for format-from-URL inference and viewer query building.
 */

/**
 * Infer format id from a URL (data URL or Kroki-style path).
 * @param {string} url - Full URL or data URL
 * @returns {string} Format id: "svg" | "png" | "txt" | "iframe" | "markdown" | "base64" (jpeg treated as png)
 */
export function formatFromUrl(url) {
  if (!url || typeof url !== "string") return "svg";
  const s = url.trim();
  const lower = s.toLowerCase();
  
  if (lower.startsWith("data:")) {
    if (lower.includes("image/svg+xml")) return "svg";
    if (lower.includes("image/png")) return "png";
    if (lower.includes("image/jpeg")) return "jpeg";
    if (lower.includes("text/plain")) return "txt";
    if (lower.includes("text/markdown")) return "markdown";
    return "base64";
  }

  // Handle ComfyUI /view URLs
  if (lower.includes("/view?filename=")) {
    if (lower.includes(".svg")) return "svg";
    if (lower.includes(".png")) return "png";
    if (lower.includes(".jpg") || lower.includes(".jpeg")) return "jpeg";
    if (lower.includes(".pdf")) return "pdf";
    if (lower.includes(".txt")) return "txt";
  }

  if (lower.includes("/svg/")) return "svg";
  if (lower.includes("/png/")) return "png";
  if (lower.includes("/jpeg/")) return "jpeg";
  if (lower.includes("/pdf/")) return "pdf";
  if (lower.includes("/txt/")) return "txt";
  if (lower.includes("/base64/")) return "base64";
  
  return "svg";
}

/**
 * Build viewer query string: url=...&format=...
 * @param {string} url - Diagram URL to encode
 * @param {string} [format] - Format id; if omitted, inferred from url via formatFromUrl
 * @param {boolean} [embed] - If true, prepend embed=1&
 * @returns {string} Query string including "?" (e.g. "?url=...&format=svg" or "?embed=1&url=...&format=svg")
 */
export function buildViewerQuery(url, format, embed) {
  const fmt = format != null && format !== "" ? format : formatFromUrl(url);
  const params = new URLSearchParams();
  if (embed) params.set("embed", "1");
  params.set("url", url);
  params.set("format", fmt);
  return "?" + params.toString();
}
