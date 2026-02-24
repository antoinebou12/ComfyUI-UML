# ComfyUI-UML

<p align="center">
  <img src="icon.png" alt="ComfyUI-UML" width="128" height="128">
</p>

ComfyUI custom nodes for rendering diagrams (Mermaid, PlantUML, Graphviz, etc.) via [Kroki](https://kroki.io) or local renderers.

## Features

- **Kroki (web)**: Many diagram types via the Kroki API. No local setup.
- **All 28 Kroki diagram types** and **output formats** (png, svg, jpeg, pdf, txt, base64) where supported by each engine. The node validates diagram type and format against [Kroki’s support matrix](https://docs.kroki.io/kroki/diagram-types).
- **Diagram options**: Optional JSON passed to Kroki for better quality (e.g. GraphViz `scale`, BlockDiag `antialias`, Mermaid/PlantUML/D2 `theme`). See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).
- **Shareable Kroki URL**: Node outputs a **kroki_url** (GET-style, deflate+base64url) so you can open the diagram in a browser or the built-in viewer.
- **Built-in viewer**: Open diagrams in a zoomable viewer with **Save locally** (download to your computer), **Save to ComfyUI** (writes to `output/uml/` so the file appears alongside node output and in any ComfyUI output/Assets browser), and copy-link. Right-click the UML node → **Open in viewer**, or go to `/extensions/ComfyUI-UML/viewer.html?url=<kroki_url>` (use the node’s **kroki_url** output).
- **ComfyUI_Viewer**: Connect the **content_for_viewer** STRING output to [ComfyUI_Viewer](https://github.com/WASasquatch/ComfyUI_Viewer); when output format is SVG, it shows the diagram in its iframe. For other formats, **content_for_viewer** is the saved file path.
- **Local Mermaid**: When backend is "local" and diagram type is Mermaid, uses [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) for offline, themeable SVG/PNG. Use the optional **theme** field (e.g. `tokyo-night`, `catppuccin-mocha`) for local Mermaid themes. You can also set the `BEAUTIFUL_MERMAID_THEME` environment variable to a built-in theme name so all local Mermaid renders use that theme (e.g. a dark theme to match ComfyUI’s dark UI). The Mermaid render script also supports ASCII export: set `BEAUTIFUL_MERMAID_OUTPUT=ascii` to output ASCII/Unicode art instead of SVG (e.g. for terminals); set `BEAUTIFUL_MERMAID_ASCII_USE_ASCII=1` for pure ASCII.
- **Local Graphviz**: Optional local Graphviz for `graphviz` diagrams when the `graphviz` Python package is installed.

## Installation

1. Clone or copy this folder into `ComfyUI/custom_nodes/`.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **(Optional) Local Mermaid**  
   To render Mermaid diagrams locally (no network):
   - Install [Node.js](https://nodejs.org/).
   - In this plugin folder, run:
     ```bash
     cd scripts
     npm install
     ```
   - For **PNG** output with local Mermaid, install CairoSVG (and system Cairo if needed):
     ```bash
     pip install cairosvg
     ```
     Without `cairosvg`, local Mermaid still works for **SVG** output; PNG will fall back to Kroki web.
4. **(Optional) SVG preview in node**  
   Installing `cairosvg` also enables a **real image preview** for SVG output: the IMAGE output will show the diagram instead of a placeholder. Without it, SVG is still saved to the `uml` folder but the IMAGE slot shows a tiny placeholder; you can open the saved SVG file or use the **kroki_url** in the viewer.
5. **(Optional) Dynamic widget visibility**  
   Installing `comfy-dynamic-widgets` (`pip install comfy-dynamic-widgets` or `pip install comfyui-uml[dynamic-widgets]`) enables **conditional visibility**: the **kroki_url** and **diagram_options** inputs are shown only when backend is **web**; **theme** is shown only when backend is **local**. Mappings are generated at load; ensure `web/js/` exists (created automatically).

## Usage

- Add the **UML Render (Mermaid/PlantUML/etc)** node (category: UML).
- Choose **backend**: `web` (Kroki API) or `local` (uses local Mermaid when diagram type is Mermaid, else falls back to web).
- Choose **diagram_type** (e.g. mermaid, plantuml, graphviz) and enter your diagram **code**.
- **output_format**: `png`, `svg`, `jpeg`, `pdf`, `txt`, or `base64`. Not every format is supported by every diagram type; the node validates against Kroki. PNG and JPEG produce a ComfyUI IMAGE; other formats are saved to disk and the IMAGE output is a placeholder (open the saved file or use **kroki_url** in the viewer).
- **diagram_options** (optional): JSON object passed to Kroki for quality/theme. Examples:
  - GraphViz: `{"scale": 1.5}` or `{"layout": "dot"}`
  - BlockDiag family: `{"antialias": ""}` for smoother PNG
  - D2 / PlantUML: `{"theme": "dark"}`
  - See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).

Outputs:

- **IMAGE**: Rendered diagram for **png**, **jpeg**, and **svg** (when cairosvg is installed); placeholder for pdf, txt, base64 (file is still saved).
- **path**: File path under ComfyUI output directory, `uml/` subfolder. Extension matches the chosen format.
- **kroki_url**: Shareable Kroki GET URL. Open in a browser or right-click node → **Open in viewer**.
- **content_for_viewer**: When format is **svg**, the raw SVG string (connect to ComfyUI_Viewer for in-UI display). Otherwise the saved file path.

### Opening the diagram in the viewer

1. **From the node**: Right-click the UML node → **Open in viewer**. The viewer opens with the current diagram loaded when the node has diagram code (the Kroki URL is built from the node’s current widgets).
2. **Manual URL**: Run the node and copy the **kroki_url** output, then open:  
   `http://localhost:8188/extensions/ComfyUI-UML/viewer.html?url=<paste_kroki_url>`  
   (Replace `<paste_kroki_url>` with the actual URL; it may need to be URL-encoded if you paste the full Kroki URL.) You can also pass a **data URL** for inline SVG: `?url=data:image/svg+xml;base64,...`.
3. Use the toolbar: zoom (Fit, 100%, ±), **Save locally**, **Save to ComfyUI**, Copy link.

### LLM + Prompt Engine workflow

You can generate diagram source with an LLM and render it with Kroki in one workflow:

1. **LLM Prompt Engine** (category UML): Builds a prompt from a template and positive/negative instructions. Use **template** with placeholders `{{description}}`, `{{diagram_type}}`, `{{format}}`, and optional **template_file** to load a preset from the `prompts/` folder (e.g. `kroki_logo.txt`). Outputs: **prompt**, **positive**, **negative**.
2. **LLM Call (OpenAI/Anthropic)** (category UML): Sends **prompt** (and optionally **negative_prompt**) to OpenAI or Anthropic. Set **OPENAI_API_KEY** or **ANTHROPIC_API_KEY** in the environment, or pass **api_key** in the node. Output **text** is compatible with the UML node’s **code_input**.
3. Connect **LLM Call** → **code_input** of **UML Render**, and set **diagram_type** (e.g. mermaid) and **output_format** (e.g. svg). Run the graph to get a diagram from the LLM-generated code.

**Workflow file**: Load **workflows/llm_kroki_logo.json** for a ready-made chain: Prompt Engine (Kroki tagline) → LLM Call → UML Render. Set your API key (environment or node) and run.

**General prompt engineering**: Add `.txt` files under **prompts/** with three blocks separated by `---`: template (first block), positive instruction (second), negative instruction (third). Use placeholders in the template. The Prompt Engine’s **template_file** dropdown will list these files so you can load and reuse them without editing the graph.

## Testing

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Config: [comfy-test.toml](comfy-test.toml). Workflows under `workflows/` are executed; to add a new one, add its filename to `[test.workflows]` `cpu` in `comfy-test.toml`.

## Workflows

Included workflow files (load from ComfyUI or open the JSON):

- **uml_quickstart.json** — Mermaid, PlantUML, GraphViz, and D2 with short examples; PNG output. Use this to try the node quickly.
- **uml_all_diagrams.json** — All 28 diagram types in a grouped layout (UML, Block/Sequence, Data, Other). One node per type with a valid format for that type.
- **uml_mermaid.json**, **uml_plantuml.json**, **uml_graphviz.json** — Single-node examples for Mermaid, PlantUML, and GraphViz.
- **llm_kroki_logo.json** — LLM + Prompt Engine → Kroki: generates diagram source from the Kroki tagline (“Creates diagrams from textual descriptions!”) via OpenAI/Anthropic and renders with the UML node. Requires an API key (see above).

## License

See repository license.

## Publishing to the Comfy Registry

The workflow in `.github/workflows/publish-node.yml` publishes this node when `pyproject.toml` changes on `main`/`master`. For it to succeed, add a repository secret:

1. Create a [personal access token](https://docs.comfy.org/registry/publishing) on the Comfy Registry for your publisher.
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**.
3. Name: `REGISTRY_ACCESS_TOKEN`, Value: your token.

Without this secret, the publish job fails with a clear error asking you to add it. If the workflow fails with "Failed to validate token", ensure the token was created for the publisher in `pyproject.toml` (`PublisherId`) and that the Comfy Registry publisher is linked to this repo.
