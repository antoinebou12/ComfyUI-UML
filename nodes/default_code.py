"""
Default diagram source per type (Kroki examples page aligned).
Used by the UMLDiagram node for initial/empty code.
See https://kroki.io/examples.html

Content is read from nodes/defaults/<type>.txt to reduce repetition and allow
editing examples without changing Python code.
"""

import os
import re

from .kroki_client import DIAGRAM_TYPES

_DEFAULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults")
_PLACEHOLDER = "// Enter your diagram source here"

# Cache per diagram type to avoid re-reading files
_cache: dict[str, str] = {}

# Safe filename: only lowercase letters and digits (diagram types contain no path chars)
_SAFE_TYPE_RE = re.compile(r"^[a-z0-9]+$")


def get_default_code(diagram_type: str) -> str:
    """Return default diagram source for the given type, or a generic placeholder.

    Reads from nodes/defaults/<type>.txt. Result is cached per type.
    """
    key = diagram_type.lower().strip()
    if key in _cache:
        return _cache[key]
    if not _SAFE_TYPE_RE.match(key) or key not in DIAGRAM_TYPES:
        return _PLACEHOLDER
    path = os.path.join(_DEFAULTS_DIR, f"{key}.txt")
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return _PLACEHOLDER
    _cache[key] = content
    return content


def _build_default_code_dict() -> dict[str, str]:
    """Build a dict of all default codes (e.g. for scripts that need to iterate)."""
    return {t: get_default_code(t) for t in DIAGRAM_TYPES}


# Optional: for scripts that need a single dict of all defaults
DEFAULT_CODE = _build_default_code_dict()
