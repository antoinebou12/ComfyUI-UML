"""
Diagram Viewer URL node: builds the viewer URL from kroki_url only.
Add this node and connect the UML Diagram kroki_url output to get
viewer_url and viewer_url_iframe strings for the browser or other nodes.
"""

from urllib.parse import quote

VIEWER_PATH = "/extensions/ComfyUI-UML/viewer.html"


def _normalize_url(value: object) -> str:
    """Normalize input to a single URL string (kroki URL)."""
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


class UMLViewerURL:
    """Build the diagram viewer page URL from kroki_url only."""

    CATEGORY = "UML"
    SEARCH_ALIASES = ["uml", "viewer", "kroki", "diagram", "open viewer"]
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("viewer_url", "viewer_url_iframe")
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "kroki_url": ("STRING", {"default": ""}),
            },
            "hidden": {},
        }

    def run(self, kroki_url: str = ""):
        url = _normalize_url(kroki_url)
        if not url:
            viewer_url = VIEWER_PATH
            viewer_url_iframe = VIEWER_PATH + "?embed=1"
        else:
            # Format inference aligned with web/viewerUrlUtils.mjs (formatFromUrl).
            url_lower = url.lower()
            if "image/svg+xml" in url_lower or "/svg/" in url_lower:
                format_param = "svg"
            elif "/png/" in url_lower or "/jpeg/" in url_lower:
                format_param = "png"
            elif "/txt/" in url_lower:
                format_param = "txt"
            else:
                format_param = "svg"
            q = "url=" + quote(url, safe="") + "&format=" + format_param
            viewer_url = VIEWER_PATH + "?" + q
            viewer_url_iframe = VIEWER_PATH + "?embed=1&" + q
        return (viewer_url, viewer_url_iframe)
