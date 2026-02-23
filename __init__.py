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

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
