"""
Viewer URL node: build the diagram viewer page URL from kroki_url or content_for_viewer.
Add this node to a workflow and connect the UML Diagram kroki_url (or content_for_viewer)
to get a string you can open in the browser or pass to other nodes.
"""

from urllib.parse import quote

VIEWER_PATH = "/extensions/ComfyUI-UML/viewer.html"


def _normalize_url(value: object) -> str:
    """Normalize input to a single URL string (kroki URL or data URL for SVG)."""
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
    """Build the diagram viewer page URL from kroki_url or content_for_viewer."""

    CATEGORY = "UML"
    SEARCH_ALIASES = ["uml", "viewer", "kroki", "diagram", "open viewer"]
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("viewer_url",)
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "kroki_url": ("STRING", {"default": ""}),
                "content_for_viewer": ("STRING", {"default": ""}),
            },
            "hidden": {},
        }

    def run(self, kroki_url: str = "", content_for_viewer: str = ""):
        # Prefer linked kroki_url, then content_for_viewer (can be SVG data URL or path), then widget
        url = _normalize_url(kroki_url) or _normalize_url(content_for_viewer)
        if not url:
            viewer_url = VIEWER_PATH
        else:
            viewer_url = VIEWER_PATH + "?url=" + quote(url, safe="")
        return (viewer_url,)
