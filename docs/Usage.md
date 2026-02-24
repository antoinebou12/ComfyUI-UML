# Usage

## Node basics

- Add the **UML Render (Mermaid/PlantUML/etc)** node (category: UML).
- **backend**: `web` (Kroki API) or `local` (local Mermaid when diagram type is Mermaid; else web).
- **diagram_type**: Choose from the supported Kroki diagram types.
- **code**: Diagram source text. When **code_input** is connected (e.g. from an LLM), it overrides this widget.
- **output_format**: `png`, `svg`, `jpeg`, `pdf`, `txt`, or `base64` — validated per type. See [KrokiFormats.md](KrokiFormats.md).
- **diagram_options** (optional): JSON for Kroki (e.g. GraphViz `{"scale": 1.5}`, BlockDiag `{"antialias": ""}`, D2/PlantUML `{"theme": "dark"}`). See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).

## Outputs

- **IMAGE**: Rendered diagram for png, jpeg, and svg (when cairosvg is installed); placeholder for pdf, txt, base64 (file still saved).
- **path**: File path under ComfyUI output directory, `uml/` subfolder; extension matches format.
- **kroki_url**: Shareable Kroki GET URL; open in browser or right-click node → **Open in viewer**.
- **content_for_viewer**: For **svg**, raw SVG string (for ComfyUI_Viewer); otherwise the saved file path.

## Opening the diagram in the viewer

1. **From the node**: Right-click the UML node → **Open in viewer** (uses current diagram code).
2. **Diagram Viewer URL node** (category UML): Add **Diagram Viewer URL** to your workflow and connect **kroki_url** from the UML Render node. The node shows a **live inline preview** of the diagram in an iframe when a URL is set (and after run); otherwise a placeholder is shown. It outputs **viewer_url** (full page) and **viewer_url_iframe** (minimal UI for iframe embedding). Right‑click the node → **Open in viewer** (new tab) or **Open in window** (popup with embed URL). See **workflows/uml_single_node.json** and **workflows/uml_mermaid.json**.
3. **Manual URL**: Copy **kroki_url** and open `http://localhost:8188/extensions/ComfyUI-UML/viewer.html?url=<paste_kroki_url>`. Data URLs supported: `?url=data:image/svg+xml;base64,...`.
4. **Toolbar**: zoom (Fit, 100%, ±), **Save locally**, **Save to ComfyUI**, Copy link.

## Embedding in an iframe

For embedding the diagram viewer inside an iframe (e.g. ComfyUI_Viewer or a custom node that displays a URL), use the **embed mode** of the same viewer so the iframe stays lightweight and sandbox-friendly:

- **URL**: `/extensions/ComfyUI-UML/viewer.html?embed=1&url=<kroki_url_or_data_url>`
- **From the node**: Connect the Diagram Viewer URL node’s **viewer_url_iframe** output to your iframe’s `src`.

The same embed URL is used for the node's inline preview and for external iframes (e.g. ComfyUI_Viewer), so behavior is consistent. The embed viewer shows the diagram with fit-to-view on load, wheel zoom, a single Fit button, and pan; it does not include Save to ComfyUI, crop, or copy actions.

## LLM + Prompt Engine workflow

1. **LLM Prompt Engine** (category UML): Builds a prompt from a template and positive/negative instructions; placeholders `{{description}}`, `{{diagram_type}}`, `{{format}}`; **template_file** loads presets from `prompts/` (e.g. `kroki_logo.txt`). Outputs: **prompt**, **positive**, **negative**.
2. **LLM Call (OpenAI/Anthropic/Ollama)** (category UML): Sends **prompt** (and optionally **negative_prompt**). For OpenAI/Anthropic set **OPENAI_API_KEY** or **ANTHROPIC_API_KEY**, or pass **api_key** in the node. For **Ollama** no key is needed; ensure Ollama is running locally and the model is pulled. Output **text** → UML node **code_input**.
3. Connect **LLM Call** → **code_input**, set **diagram_type** and **output_format**, run to get diagram from LLM-generated code.

**Workflow file**: Load **workflows/llm_kroki_logo.json** for Prompt Engine → LLM Call → UML Render. Set API key and run.

**Prompt files**: Add `.txt` under **prompts/** with three blocks separated by `---`: template, positive, negative. Use placeholders; **template_file** dropdown lists them. See [LLMPromptEngine.md](LLMPromptEngine.md) and [LLMCall.md](LLMCall.md).

## See also

- [KrokiFormats.md](KrokiFormats.md) — diagram type × format table
- [UMLDiagram.md](UMLDiagram.md) — UML Render node reference
- [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/)
