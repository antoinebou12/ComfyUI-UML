"""
ComFyUML — ComfyUI UML: custom nodes for generating diagrams via Kroki.
"""

try:
    import os as _os
    if _os.environ.get("COMFYUI_UML_SKIP_COMFY_ENV", "").strip().lower() not in ("1", "true", "yes"):
        from comfy_env import install
        try:
            install()
        except Exception as e:
            print("ComfyUI-UML: comfy_env install failed (nodes will still load): %s" % (e,))
except ImportError:
    import os as _os
    if _os.environ.get("COMFYUI_UML_SKIP_COMFY_ENV", "").strip().lower() not in ("1", "true", "yes"):
        try:
            from install import install as _local_install
            _local_install()
        except Exception as e:
            print("ComfyUI-UML: local install failed (nodes will still load): %s" % (e,))

import os
import sys
import importlib.util

# Ensure plugin root is on path for other imports (e.g. kroki_client)
_plugin_root = os.path.dirname(os.path.abspath(__file__))
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

# Load our nodes package explicitly so we never pick up ComfyUI's core "nodes" module.
# ComfyUI may load this __init__.py via importlib from file, so relative imports can fail;
# and sys.modules["nodes"] is already ComfyUI's nodes. Use a unique module name.
_nodes_pkg_path = os.path.join(_plugin_root, "nodes", "__init__.py")
_nodes_spec = importlib.util.spec_from_file_location(
    "comfyui_uml_nodes",
    _nodes_pkg_path,
    submodule_search_locations=[os.path.join(_plugin_root, "nodes")],
)
_uml_nodes = importlib.util.module_from_spec(_nodes_spec)
sys.modules["comfyui_uml_nodes"] = _uml_nodes
_nodes_spec.loader.exec_module(_uml_nodes)
NODE_CLASS_MAPPINGS = _uml_nodes.NODE_CLASS_MAPPINGS
NODE_DISPLAY_NAME_MAPPINGS = _uml_nodes.NODE_DISPLAY_NAME_MAPPINGS

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
    from comfyui_uml_nodes.uml_routes import register_routes

    register_routes()
except Exception:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
