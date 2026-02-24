"""
UML Code Assistant: single node that builds prompt from template/prompts/ and calls LLM (Ollama, OpenAI, Anthropic, Gemini).
Output flows directly into UML Render (UMLDiagram) code_input.
"""

from types import SimpleNamespace

from .uml_llm_shared import (
    ANTHROPIC_MODELS,
    GEMINI_MODELS,
    OLLAMA_MODELS,
    OPENAI_MODELS,
    MOCK_LLM_RESPONSE,
    apply_placeholders,
    call_anthropic,
    call_gemini,
    call_ollama,
    call_openai,
    list_prompt_files,
    load_prompt_file,
    resolve_api_key,
    resolve_ollama_base_url,
    use_mock_llm,
)


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
        files = list_prompt_files()
        template_file_choices = [""] + files
        provider_choices = ["ollama", "openai", "anthropic", "gemini"]
        model_choices = OLLAMA_MODELS + OPENAI_MODELS + ANTHROPIC_MODELS + GEMINI_MODELS
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
        if (template_file or "").strip():
            t, p, n = load_prompt_file(template_file.strip())
            if t:
                template = t
            if p:
                positive_instruction = p
            if n:
                negative_instruction = n

        desc = (description or "").strip()
        dt = (diagram_type or "").strip()
        fmt = (output_format or "").strip()
        template = apply_placeholders((template or "").strip(), desc, dt, fmt)
        positive_instruction = apply_placeholders(
            (positive_instruction or "").strip(), desc, dt, fmt
        )
        negative_instruction = apply_placeholders(
            (negative_instruction or "").strip(), desc, dt, fmt
        )

        prompt = template
        if positive_instruction:
            prompt = prompt + "\n\nInstructions: " + positive_instruction

        if use_mock_llm():
            result = SimpleNamespace(content=MOCK_LLM_RESPONSE, text=MOCK_LLM_RESPONSE)
            return (result,)

        if provider == "ollama":
            base_url = resolve_ollama_base_url(ollama_base_url)
            text = call_ollama(prompt, negative_instruction, model, base_url)
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
                text = call_openai(prompt, negative_instruction, model, key)
            elif provider == "gemini":
                text = call_gemini(prompt, negative_instruction, model, key)
            else:
                text = call_anthropic(prompt, negative_instruction, model, key)

        result = SimpleNamespace(content=text, text=text)
        return (result,)
