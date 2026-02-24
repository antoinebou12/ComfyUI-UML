"""Build viewer URL from kroki_url or content_for_viewer (SVG string / file path)."""

import base64
import os
from urllib.parse import quote

VIEWER_PATH = "/extensions/ComfyUI-UML/viewer.html"

# Format from data URL content-type or path/Kroki URL
_DATA_URL_FORMAT = {
    "image/svg": "svg",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "text/plain": "txt",
    "text/markdown": "markdown",
}
_EXT_FORMAT = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".svg": "svg", ".pdf": "pdf", ".txt": "txt"}
_URL_PATH_FORMAT = {"/svg/": "svg", "/png/": "png", "/jpeg/": "jpeg", "/pdf/": "pdf", "/txt/": "txt", "/base64/": "base64"}


def _normalize_url(value: object) -> str:
    """Single string from wire input (string, tuple[0], or object.text/content/output)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (tuple, list)) and len(value):
        return _normalize_url(value[0])
    for attr in ("text", "assistant_response", "content", "output"):
        if hasattr(value, attr):
            v = getattr(value, attr)
            if v is not None and isinstance(v, str):
                return v.strip()
    return str(value).strip()


def _viewer_query(url: str) -> str:
    """Build query string url=...&format=... for the viewer from kroki_url or content_for_viewer."""
    url_lower = url.lower()
    # Raw SVG
    if url.lstrip().startswith(("<?xml", "<svg")):
        b64 = base64.b64encode(url.encode("utf-8")).decode("ascii")
        encoded = quote(f"data:image/svg+xml;base64,{b64}", safe="")
        return f"url={encoded}&format=svg"
    # Data URL
    if url_lower.startswith("data:"):
        fmt = next((v for k, v in _DATA_URL_FORMAT.items() if k in url_lower), "base64")
        return f"url={quote(url, safe='')}&format={fmt}"
    # Local file path
    if "://" not in url and (os.path.isabs(url) or "/" in url.replace("\\", "/")):
        filename = os.path.basename(url.replace("\\", "/"))
        view_url = f"/view?filename={quote(filename)}&subfolder=uml&type=output"
        ext = os.path.splitext(filename)[1].lower()
        fmt = _EXT_FORMAT.get(ext, "png")
        return f"url={quote(view_url, safe='')}&format={fmt}"
    # Kroki or other web URL
    fmt = next((v for k, v in _URL_PATH_FORMAT.items() if k in url_lower), "svg")
    return f"url={quote(url, safe='')}&format={fmt}"


class UMLViewerURL:
    """Build viewer URL and iframe URL from kroki_url or content_for_viewer."""

    CATEGORY = "UML"
    SEARCH_ALIASES = ["uml", "viewer", "kroki", "diagram", "open viewer"]
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("viewer_url", "viewer_url_iframe")
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}, "optional": {"kroki_url": ("STRING", {"default": ""})}, "hidden": {}}

    def run(self, kroki_url: str = ""):
        url = _normalize_url(kroki_url)
        if not url:
            return (VIEWER_PATH, VIEWER_PATH + "?embed=1")
        q = _viewer_query(url)
        return (VIEWER_PATH + "?" + q, VIEWER_PATH + "?embed=1&" + q)
