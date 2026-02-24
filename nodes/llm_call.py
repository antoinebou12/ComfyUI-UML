"""
LLM Call node: call OpenAI or Anthropic API with prompt + optional negative prompt; output compatible with UMLDiagram code_input.
"""

import os
from types import SimpleNamespace

import httpx

# Provider config: (base_url, model_param_key, default_models)
_OPENAI_BASE = "https://api.openai.com/v1"
_ANTHROPIC_BASE = "https://api.anthropic.com"

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


class LLMCall:
    """Call an LLM (OpenAI or Anthropic) with prompt and optional negative prompt; output has .content for UMLDiagram code_input."""

    CATEGORY = "UML"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        provider_choices = ["openai", "anthropic"]
        model_choices = OPENAI_MODELS + ANTHROPIC_MODELS
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "provider": (provider_choices, {"default": "openai"}),
                "model": (model_choices, {"default": "gpt-4o-mini"}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def run(
        self,
        prompt: str,
        provider: str,
        model: str,
        negative_prompt: str = "",
        api_key: str = "",
    ):
        prompt = (prompt or "").strip()
        key = (api_key or "").strip() or os.environ.get(
            "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY", ""
        )
        if not key:
            raise RuntimeError(
                "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in the environment, or pass api_key to the node."
            )
        negative = (negative_prompt or "").strip()

        if provider == "openai":
            text = self._call_openai(prompt, negative, model, key)
        else:
            text = self._call_anthropic(prompt, negative, model, key)

        # Return object with .content so UMLDiagram _normalize_to_code() accepts it
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
