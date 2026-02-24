"""ComfyUI-UML nodes: diagram rendering (Kroki API), prompt engine, LLM call."""

from .llm_call import LLMCall
from .prompt_engine import LLMPromptEngine
from .uml_diagram import UMLDiagram

NODE_CLASS_MAPPINGS = {
    "LLMCall": LLMCall,
    "LLMPromptEngine": LLMPromptEngine,
    "UMLDiagram": UMLDiagram,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMCall": "LLM Call (OpenAI/Anthropic)",
    "LLMPromptEngine": "LLM Prompt Engine",
    "UMLDiagram": "UML Render (Mermaid/PlantUML/etc)",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "LLMCall",
    "LLMPromptEngine",
    "UMLDiagram",
]
