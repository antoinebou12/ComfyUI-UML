# LLM Call (OpenAI/Anthropic)

Calls an LLM (OpenAI or Anthropic) with a prompt and optional negative prompt. The **text** output is compatible with the UML Render node's **code_input** for generating diagram source from natural language.

## Parameters

- **prompt**: The main prompt text (multiline).
- **provider**: `openai` or `anthropic`.
- **model**: Model name (e.g. gpt-4o-mini, claude-3-5-haiku-20241022).
- **negative_prompt**: Optional; passed as a second message or instruction where supported.
- **api_key**: Optional; if empty, uses `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` from the environment.

## Outputs

- **text**: The model's response. Connect to **UML Render** → **code_input** to render as a diagram.

## Usage

Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the environment, or set **api_key** in the node. Connect **prompt** from **LLM Prompt Engine** or any string source, then connect **text** to **UML Render** → **code_input**.
