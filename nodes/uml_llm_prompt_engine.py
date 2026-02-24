"""
LLM Prompt Engine: builds a prompt from template and positive/negative instructions.
Outputs prompt, positive, negative for use with LLMCall.
"""

from .kroki_client import DIAGRAM_TYPES
from .uml_llm_shared import (
    apply_placeholders,
    list_prompt_files,
    load_prompt_file,
)


class LLMPromptEngine:
    """
    Builds an LLM prompt from a template and positive/negative instructions.
    Optionally loads a preset from the prompts/ folder.
    """

    CATEGORY = "UML"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "positive", "negative")
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        files = list_prompt_files()
        template_file_choices = [""] + files
        return {
            "required": {},
            "optional": {
                "template": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Generate a Mermaid diagram that illustrates: {{description}}",
                    },
                ),
                "description": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "Kroki – Creates diagrams from textual descriptions!",
                    },
                ),
                "positive": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Output only valid Mermaid diagram code. No markdown fences (no ```). No explanation.",
                    },
                ),
                "negative": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Do not add any text outside the diagram syntax.",
                    },
                ),
                "template_file": (template_file_choices, {"default": ""}),
                "diagram_type": (DIAGRAM_TYPES, {"default": "mermaid"}),
                "output_format": (
                    ["png", "svg", "jpeg", "pdf", "txt", "base64"],
                    {"default": "svg"},
                ),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def run(
        self,
        template: str = "",
        description: str = "",
        positive: str = "",
        negative: str = "",
        template_file: str = "",
        diagram_type: str = "mermaid",
        output_format: str = "svg",
    ):
        if (template_file or "").strip():
            t, p, n = load_prompt_file(template_file.strip())
            if t:
                template = t
            if p:
                positive = p
            if n:
                negative = n

        desc = (description or "").strip()
        dt = (diagram_type or "").strip()
        fmt = (output_format or "").strip()
        template = apply_placeholders((template or "").strip(), desc, dt, fmt)
        positive_out = apply_placeholders((positive or "").strip(), desc, dt, fmt)
        negative_out = apply_placeholders((negative or "").strip(), desc, dt, fmt)

        return (template, positive_out, negative_out)
