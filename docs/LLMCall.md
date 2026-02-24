# LLM Call (OpenAI/Anthropic/Ollama)

Calls an LLM (OpenAI, Anthropic, or Ollama) with a prompt and optional negative prompt. The **text** output is compatible with the UML Render node's **code_input** for generating diagram source from natural language.

## Parameters

- **prompt**: The main prompt text (multiline).
- **provider**: `openai`, `anthropic`, or `ollama`.
- **model**: Model name (e.g. gpt-4o-mini, claude-3-5-haiku-20241022, llama3.2).
- **negative_prompt**: Optional; passed as a second message or instruction where supported.
- **api_key**: Optional; if empty, uses `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` from the environment. Not used when provider is `ollama`.
- **ollama_base_url**: Optional; only for provider `ollama`. Base URL for the Ollama API (default `http://localhost:11434`, or set `OLLAMA_BASE_URL` in the environment). When provider is **ollama**, the model list is loaded from the Ollama server at this URL; use the **Refresh models** button on the node to update the list after starting Ollama or pulling new models.

## Outputs

- **text**: The model's response. Connect to **UML Render** → **code_input** to render as a diagram.

## Usage

- **OpenAI / Anthropic**: Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the environment, or set **api_key** in the node.
- **Ollama**: No API key needed. Ensure Ollama is running locally (e.g. `ollama serve`) and the chosen model is pulled (e.g. `ollama pull llama3.2`). Use **ollama_base_url** only if Ollama is not on `http://localhost:11434`. The node fetches the list of available models from the server when provider is Ollama; use **Refresh models** to update the dropdown after installing or removing models.

Connect **prompt** from **LLM Prompt Engine** or any string source, then connect **text** to **UML Render** → **code_input**.
