# LLM Prompt Engine

Builds an LLM prompt from a template and positive/negative instructions. Optionally loads a preset from the **prompts/** folder (e.g. `kroki_logo.txt`).

## Parameters

- **template**: Template text with placeholders `{{description}}`, `{{diagram_type}}`, `{{format}}`.
- **template_file**: Optional; load a preset from **prompts/** (dropdown lists `.txt` files). File format: three blocks separated by `---` (template, positive, negative).
- **description**: Text to substitute for `{{description}}`.
- **diagram_type**: Substitute for `{{diagram_type}}`.
- **output_format**: Substitute for `{{format}}`.
- **positive**: Positive instruction block (or from file).
- **negative**: Negative instruction block (or from file).

## Outputs

- **prompt**: Full prompt string. Connect to **LLM Call** → **prompt**.
- **positive**: Positive instruction string.
- **negative**: Negative instruction string.

## Usage

Use **template_file** to load presets from **prompts/** (e.g. `general_mermaid.txt`, `kroki_logo.txt`). Connect **prompt** to **LLM Call** and **LLM Call** → **text** to **UML Render** → **code_input** for a full LLM → diagram pipeline.
