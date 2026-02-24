"""
LLM Call: calls OpenAI, Anthropic, or Ollama with a prompt and optional negative prompt.
Output text connects to UML Render (UMLDiagram) code_input.
"""

from .uml_llm_shared import (
    ANTHROPIC_MODELS,
    GEMINI_MODELS,
    OLLAMA_MODELS,
    OPENAI_MODELS,
    MOCK_LLM_RESPONSE,
    call_anthropic,
    call_gemini,
    call_ollama,
    call_openai,
    resolve_api_key,
    resolve_ollama_base_url,
    use_mock_llm,
)


class LLMCall:
    """
    Calls an LLM (OpenAI, Anthropic, Gemini, or Ollama) with a prompt and optional negative prompt.
    Output text is compatible with UML Render code_input.
    """

    CATEGORY = "UML"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        provider_choices = ["ollama", "openai", "anthropic", "gemini"]
        model_choices = OLLAMA_MODELS + OPENAI_MODELS + ANTHROPIC_MODELS + GEMINI_MODELS
        return {
            "required": {},
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "provider": (provider_choices, {"default": "ollama"}),
                "model": (model_choices, {"default": "llama3.2"}),
                "ollama_base_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def run(
        self,
        prompt: str = "",
        negative_prompt: str = "",
        api_key: str = "",
        provider: str = "ollama",
        model: str = "llama3.2",
        ollama_base_url: str = "",
    ):
        prompt = (prompt or "").strip()
        negative_prompt = (negative_prompt or "").strip()

        if use_mock_llm():
            return (MOCK_LLM_RESPONSE,)

        if provider == "ollama":
            base_url = resolve_ollama_base_url(ollama_base_url)
            text = call_ollama(prompt, negative_prompt, model, base_url)
        else:
            key = resolve_api_key(provider, api_key)
            if not key:
                env_hint = (
                    "Set GEMINI_API_KEY in the environment, or pass api_key to the node."
                    if provider == "gemini"
                    else "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in the environment, or pass api_key to the node."
                )
                raise RuntimeError(env_hint)
            if provider == "openai":
                text = call_openai(prompt, negative_prompt, model, key)
            elif provider == "gemini":
                text = call_gemini(prompt, negative_prompt, model, key)
            else:
                text = call_anthropic(prompt, negative_prompt, model, key)

        return (text,)
