"""ComfyUI-UML nodes: diagram rendering (Kroki API), UML Code Assistant (LLM)."""

from .uml_diagram import UMLDiagram
from .uml_llm import UMLLLMCodeGenerator
from .uml_viewer_url import UMLViewerURL

NODE_CLASS_MAPPINGS = {
    "UMLLLMCodeGenerator": UMLLLMCodeGenerator,
    "UMLDiagram": UMLDiagram,
    "UMLViewerURL": UMLViewerURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UMLLLMCodeGenerator": "UML Code Assistant",
    "UMLDiagram": "UML Render",
    "UMLViewerURL": "Diagram Viewer URL",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "UMLLLMCodeGenerator",
    "UMLDiagram",
    "UMLViewerURL",
]
