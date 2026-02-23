"""ComfyUI-UML nodes: diagram rendering (Kroki API)."""

from .uml_diagram import UMLDiagram

NODE_CLASS_MAPPINGS = {
    "UMLDiagram": UMLDiagram,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UMLDiagram": "UML Render (Mermaid/PlantUML/etc)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "UMLDiagram"]
