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

Use **template_file** to load presets from **prompts/** (e.g. `general_mermaid.txt`, `kroki.txt`, `uml_plan_then_code.txt`). Connect **prompt** to **LLM Call** and **LLM Call** → **text** to **UML Render** → **code_input** for a full LLM → diagram pipeline.

### Plan-then-code presets

- **`uml_plan_then_code.txt`** — Aligns with uml-mcp’s plan-first flow: scope limits, Kroki **backend** name (`{{diagram_type}}`) must match **UML Render**, then DSL-only output (same spirit as the **`uml_diagram_with_thinking`** MCP prompt).
- **`plantuml_sequence.txt`** — Sequence-focused PlantUML; set **UML Render** → **diagram_type** to **plantuml**.
- **`mermaid_flowchart.txt`** — Flowchart/graph Mermaid; set **diagram_type** to **mermaid**.

### uml-mcp vs this stack

**uml-mcp** uses logical types (`class`, `sequence`, …) and tools like **`generate_uml`**. **ComfyUI-UML** uses **Kroki backend** strings in **UML Render** (`plantuml`, `mermaid`, …). Presets spell this out so the LLM does not confuse MCP logical names with Comfy **diagram_type** widgets.

See [UMLDiagram.md](UMLDiagram.md) for parameter details.
