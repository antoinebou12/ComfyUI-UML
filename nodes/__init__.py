"""ComfyUI-UML nodes: diagram rendering (Kroki API), UML Code Assistant (LLM), LLM Prompt Engine, LLM Call."""

from .uml_diagram import UMLDiagram
from .uml_llm import UMLLLMCodeGenerator
from .uml_llm_call import LLMCall
from .uml_llm_prompt_engine import LLMPromptEngine
from .uml_viewer_url import UMLViewerURL

NODE_CLASS_MAPPINGS = {
    "LLMCall": LLMCall,
    "LLMPromptEngine": LLMPromptEngine,
    "UMLLLMCodeGenerator": UMLLLMCodeGenerator,
    "UMLDiagram": UMLDiagram,
    "UMLViewerURL": UMLViewerURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMCall": "LLM Call",
    "LLMPromptEngine": "LLM Prompt Engine",
    "UMLLLMCodeGenerator": "UML Code Assistant",
    "UMLDiagram": "UML Render",
    "UMLViewerURL": "Diagram Viewer URL",
}

__all__ = [
    "LLMCall",
    "LLMPromptEngine",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "UMLLLMCodeGenerator",
    "UMLDiagram",
    "UMLViewerURL",
]
