"""
Shared helpers for LLM prompt building and LLM API calls (LLMPromptEngine, LLMCall, UMLLLMCodeGenerator).
"""

import os
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

# --- Prompts directory and helpers ---
def prompts_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts"


def list_prompt_files() -> list[str]:
    d = prompts_dir()
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.glob("*.txt"))


def load_prompt_file(name: str) -> tuple[str, str, str]:
    path = prompts_dir() / name
    if not path.is_file():
        return "", "", ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    parts = [p.strip() for p in raw.split("\n---\n")]
    template = parts[0] if len(parts) > 0 else ""
    positive = parts[1] if len(parts) > 1 else ""
    negative = parts[2] if len(parts) > 2 else ""
    return template, positive, negative


def apply_placeholders(
    text: str, description: str, diagram_type: str = "", format_name: str = ""
) -> str:
    text = text.replace("{{description}}", description)
    text = text.replace("{{diagram_type}}", diagram_type)
    text = text.replace("{{format}}", format_name)
    return text


# --- Mock LLM for CI (comfy-test) ---
# When COMFY_UI_UML_MOCK_LLM=1, LLMCall and UMLLLMCodeGenerator return this instead of calling APIs.
MOCK_LLM_RESPONSE = "graph LR\n  A[Kroki] --> B[Diagrams]"


def use_mock_llm() -> bool:
    return os.environ.get("COMFY_UI_UML_MOCK_LLM", "").strip() == "1"


# --- LLM provider config ---
OPENAI_BASE = "https://api.openai.com/v1"
ANTHROPIC_BASE = "https://api.anthropic.com"
OLLAMA_BASE = "http://localhost:11434"
GEMINI_BASE = "https://generativelanguage.googleapis.com"

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
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
]


def call_openai(prompt: str, negative: str, model: str, api_key: str) -> str:
    if httpx is None:
        raise RuntimeError("httpx is required for LLM calls")
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
            f"{OPENAI_BASE}/chat/completions",
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


def call_anthropic(prompt: str, negative: str, model: str, api_key: str) -> str:
    if httpx is None:
        raise RuntimeError("httpx is required for LLM calls")
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if negative:
        payload["system"] = "Do NOT do the following: " + negative
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{ANTHROPIC_BASE}/v1/messages",
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


def call_gemini(prompt: str, negative: str, model: str, api_key: str) -> str:
    if httpx is None:
        raise RuntimeError("httpx is required for LLM calls")
    url = f"{GEMINI_BASE}/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4096},
    }
    if negative:
        payload["systemInstruction"] = {
            "role": "system",
            "parts": [{"text": "Do NOT do the following: " + negative}],
        }
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            url,
            params={"key": api_key},
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    content = candidates[0].get("content")
    if not content or not isinstance(content, dict):
        raise RuntimeError("Gemini returned no content in candidate")
    parts = content.get("parts") or []
    if not parts or not isinstance(parts[0], dict):
        raise RuntimeError("Gemini returned no text in content")
    text = parts[0].get("text")
    if text is None:
        raise RuntimeError("Gemini returned no text in content")
    return (text if isinstance(text, str) else str(text)).strip()


def call_ollama(prompt: str, negative: str, model: str, base_url: str) -> str:
    if httpx is None:
        raise RuntimeError("httpx is required for LLM calls")
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


def resolve_ollama_base_url(ollama_base_url: str) -> str:
    base_url = (
        (ollama_base_url or "").strip()
        or os.environ.get("OLLAMA_BASE_URL", "").strip()
        or OLLAMA_BASE
    )
    return base_url.rstrip("/")


def resolve_api_key(provider: str, api_key: str) -> str:
    key = (api_key or "").strip()
    if key:
        return key
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    env_key = env_map.get(provider, "")
    return os.environ.get(env_key, "").strip()
