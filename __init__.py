"""
ComFyUML — ComfyUI UML: custom nodes for generating diagrams via Kroki.
"""

try:
    from comfy_env import install
    install()
except Exception:
    pass

import os
import sys

# Ensure plugin root is on path for kroki_client
_plugin_root = os.path.dirname(os.path.abspath(__file__))
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Generate visibility mappings for comfy-dynamic-widgets (optional)
try:
    from comfy_dynamic_widgets import write_mappings
    _web_js = os.path.join(os.path.dirname(__file__), "web", "js")
    os.makedirs(_web_js, exist_ok=True)
    write_mappings(NODE_CLASS_MAPPINGS, __file__)
except ImportError:
    pass

# Web viewer: open /extensions/ComfyUI-UML/viewer.html?url=<kroki_url>
WEB_DIRECTORY = "./web"

# Register API route for viewer "Save to ComfyUI" (writes to output/uml/)
try:
    from nodes.uml_routes import register_routes
    register_routes()
except Exception:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
