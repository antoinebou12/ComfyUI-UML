"""
UML Code Assistant: single node that builds prompt from template/prompts/ and calls LLM (Ollama, OpenAI, Anthropic).
Output flows directly into UML Render (UMLDiagram) code_input.
"""

import os
from pathlib import Path
from types import SimpleNamespace

import httpx

# --- Prompts directory and helpers (from prompt_engine) ---
def _prompts_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts"


def _list_prompt_files() -> list[str]:
    d = _prompts_dir()
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.glob("*.txt"))


def _load_prompt_file(name: str) -> tuple[str, str, str]:
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
    text = text.replace("{{description}}", description)
    text = text.replace("{{diagram_type}}", diagram_type)
    text = text.replace("{{format}}", format_name)
    return text


# --- LLM provider config (from llm_call) ---
_OPENAI_BASE = "https://api.openai.com/v1"
_ANTHROPIC_BASE = "https://api.anthropic.com"
_OLLAMA_BASE = "http://localhost:11434"

OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]
ANTHROPIC_MODELS = [
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
]
OLLAMA_MODELS = [
    "llama3.2",
    "llama3.1",
    "mistral",
    "codellama",
    "qwen2.5-coder",
    "phi3",
    "gemma2",
]


class UMLLLMCodeGenerator:
    """
    UML Code Assistant: format prompt from template + prompts/, call LLM; output is code_input for UML Render.
    Default provider: Ollama; default model: llama3.2.
    """

    CATEGORY = "UML"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("code_input",)
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        files = _list_prompt_files()
        template_file_choices = [""] + files
        provider_choices = ["ollama", "openai", "anthropic"]
        model_choices = OLLAMA_MODELS + OPENAI_MODELS + ANTHROPIC_MODELS
        return {
            "required": {
                "description": (
                    "STRING",
                    {
                        "default": "Kroki – Creates diagrams from textual descriptions!",
                        "multiline": False,
                    },
                ),
            },
            "optional": {
                "template": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Generate a Mermaid diagram that illustrates: {{description}}",
                    },
                ),
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
                "provider": (provider_choices, {"default": "ollama"}),
                "model": (model_choices, {"default": "llama3.2"}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "ollama_base_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def run(
        self,
        description: str,
        template: str = "",
        positive_instruction: str = "",
        negative_instruction: str = "",
        template_file: str = "",
        diagram_type: str = "mermaid",
        output_format: str = "svg",
        provider: str = "ollama",
        model: str = "llama3.2",
        api_key: str = "",
        ollama_base_url: str = "",
    ):
        # Load from prompts/ if file selected
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
        template = _apply_placeholders((template or "").strip(), desc, dt, fmt)
        positive_instruction = _apply_placeholders(
            (positive_instruction or "").strip(), desc, dt, fmt
        )
        negative_instruction = _apply_placeholders(
            (negative_instruction or "").strip(), desc, dt, fmt
        )

        prompt = template
        if positive_instruction:
            prompt = prompt + "\n\nInstructions: " + positive_instruction

        if provider == "ollama":
            base_url = (
                (ollama_base_url or "").strip()
                or os.environ.get("OLLAMA_BASE_URL", "").strip()
                or _OLLAMA_BASE
            )
            base_url = base_url.rstrip("/")
            text = self._call_ollama(prompt, negative_instruction, model, base_url)
        else:
            key = (api_key or "").strip() or os.environ.get(
                "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY", ""
            )
            if not key:
                raise RuntimeError(
                    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in the environment, or pass api_key to the node."
                )
            if provider == "openai":
                text = self._call_openai(prompt, negative_instruction, model, key)
            else:
                text = self._call_anthropic(prompt, negative_instruction, model, key)

        result = SimpleNamespace(content=text, text=text)
        return (result,)

    def _call_openai(self, prompt: str, negative: str, model: str, api_key: str) -> str:
        messages = []
        if negative:
            messages.append({"role": "system", "content": "Do NOT do the following: " + negative})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{_OPENAI_BASE}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI returned no choices")
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()

    def _call_anthropic(self, prompt: str, negative: str, model: str, api_key: str) -> str:
        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if negative:
            payload["system"] = "Do NOT do the following: " + negative
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{_ANTHROPIC_BASE}/v1/messages",
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )
            r.raise_for_status()
            data = r.json()
        content = data.get("content") or []
        for block in content:
            if block.get("type") == "text":
                return (block.get("text") or "").strip()
        raise RuntimeError("Anthropic returned no text content")

    def _call_ollama(self, prompt: str, negative: str, model: str, base_url: str) -> str:
        messages = []
        if negative:
            messages.append({"role": "system", "content": "Do NOT do the following: " + negative})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "stream": False}
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                f"{base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        msg = data.get("message")
        if not msg or not isinstance(msg, dict):
            raise RuntimeError("Ollama returned no message")
        content = msg.get("content")
        if content is None:
            raise RuntimeError("Ollama returned no content in message")
        return (content if isinstance(content, str) else str(content)).strip()
