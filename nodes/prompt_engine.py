"""
LLM Prompt Engine node: build prompt from template + positive/negative, optional load from prompts/.
"""

from pathlib import Path


# Prompts directory at repo root (next to nodes/)
def _prompts_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts"


def _list_prompt_files() -> list[str]:
    """Return list of .txt filenames (no path) in prompts/, sorted."""
    d = _prompts_dir()
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.glob("*.txt"))


def _load_prompt_file(name: str) -> tuple[str, str, str]:
    """Load template, positive, negative from prompts/<name>.txt. Format: blocks separated by ---."""
    path = _prompts_dir() / name
    if not path.is_file():
        return "", "", ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    parts = [p.strip() for p in raw.split("\n---\n")]
    template = parts[0] if len(parts) > 0 else ""
    positive = parts[1] if len(parts) > 1 else ""
    negative = parts[2] if len(parts) > 2 else ""
    return template, positive, negative


def _apply_placeholders(
    text: str, description: str, diagram_type: str = "", format_name: str = ""
) -> str:
    """Replace {{description}}, {{diagram_type}}, {{format}} in text."""
    text = text.replace("{{description}}", description)
    text = text.replace("{{diagram_type}}", diagram_type)
    text = text.replace("{{format}}", format_name)
    return text


class LLMPromptEngine:
    """Build LLM prompt from template + positive/negative instructions; optional load from prompts/."""

    CATEGORY = "UML"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "positive", "negative")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        files = _list_prompt_files()
        template_file_choices = [""] + files
        return {
            "required": {
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
                        "default": "Kroki – Creates diagrams from textual descriptions!",
                        "multiline": False,
                    },
                ),
            },
            "optional": {
                "positive_instruction": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Output only valid Mermaid diagram code. No markdown fences (no ```). No explanation.",
                    },
                ),
                "negative_instruction": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Do not add any text outside the diagram syntax.",
                    },
                ),
                "template_file": (template_file_choices, {"default": ""}),
                "diagram_type": ("STRING", {"default": "mermaid", "multiline": False}),
                "output_format": ("STRING", {"default": "svg", "multiline": False}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def run(
        self,
        template: str,
        description: str,
        positive_instruction: str = "",
        negative_instruction: str = "",
        template_file: str = "",
        diagram_type: str = "mermaid",
        output_format: str = "svg",
    ):
        if (template_file or "").strip():
            t, p, n = _load_prompt_file(template_file.strip())
            if t:
                template = t
            if p:
                positive_instruction = p
            if n:
                negative_instruction = n

        desc = (description or "").strip()
        dt = (diagram_type or "").strip()
        fmt = (output_format or "").strip()
        template = _apply_placeholders(template, desc, dt, fmt)
        positive_instruction = _apply_placeholders(
            (positive_instruction or "").strip(), desc, dt, fmt
        )
        negative_instruction = _apply_placeholders(
            (negative_instruction or "").strip(), desc, dt, fmt
        )

        # Full prompt: template + positive as instructions (so one string for simple LLM nodes)
        prompt = template
        if positive_instruction:
            prompt = prompt + "\n\nInstructions: " + positive_instruction

        return (prompt, positive_instruction, negative_instruction)
