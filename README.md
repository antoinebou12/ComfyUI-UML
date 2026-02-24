# ComfyUI-UML

[![PR Gate](https://github.com/antoinebou12/ComfyUI-UML/actions/workflows/pr-gate.yml/badge.svg)](https://github.com/antoinebou12/ComfyUI-UML/actions/workflows/pr-gate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Comfy Registry](https://img.shields.io/badge/Comfy_Registry-comfyui--uml-blue)](https://registry.comfy.org/publishers/antoinebou12/nodes/comfyui-uml)

<p align="center">
  <img src="icon.png" alt="ComfyUI-UML" width="128" height="128">
</p>

ComfyUI custom nodes for rendering diagrams (Mermaid, PlantUML, Graphviz, etc.) via [Kroki](https://kroki.io) or local renderers.

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Updating](#updating)
- [Usage](#usage)
- [Kroki diagram types and format support](#kroki-diagram-types-and-format-support)
- [Testing](#testing)
- [Workflows](#workflows)
- [License](#license)
- [Publishing to the Comfy Registry](#publishing-to-the-comfy-registry)

## Features

- **Kroki (web)**: Many diagram types via the Kroki API. No local setup.
- **All 28 Kroki diagram types** and **output formats** (png, svg, jpeg, pdf, txt, base64) as supported by each diagram type; diagram type and format validated against [Kroki’s support matrix](https://docs.kroki.io/kroki/diagram-types). (Details in [Usage](#usage).)
- **Diagram options**: Optional JSON passed to Kroki for quality/theme (e.g. GraphViz `scale`, BlockDiag `antialias`, Mermaid/PlantUML/D2 `theme`). See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).
- **Shareable Kroki URL**: Node outputs **kroki_url** (GET-style, deflate+base64url) to open in a browser or the built-in viewer.
- **Built-in viewer**: Right-click node → **Open in viewer**; zoom, **Save locally**, **Save to ComfyUI** (`output/uml/`), copy link. Or open `/extensions/ComfyUI-UML/viewer.html?url=<kroki_url>`.
- **ComfyUI_Viewer**: Connect **content_for_viewer** to [ComfyUI_Viewer](https://github.com/WASasquatch/ComfyUI_Viewer); SVG shows in iframe; other formats use saved file path.
- **Local Mermaid**: Backend "local" + Mermaid uses [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) for offline, themeable SVG/PNG. Optional **theme** (e.g. `tokyo-night`) or `BEAUTIFUL_MERMAID_THEME`. ASCII export via `BEAUTIFUL_MERMAID_OUTPUT=ascii`.
- **Local Graphviz**: Optional local Graphviz when the `graphviz` Python package is installed.

**Outputs**: IMAGE, path, kroki_url, content_for_viewer (details in [Usage](#usage)).

## Installation

1. Clone or copy this folder into `ComfyUI/custom_nodes/`.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or with uv: `uv sync`.
3. **Optional** — Local Mermaid, SVG preview, dynamic widgets:
   - **Local Mermaid**: Install [Node.js](https://nodejs.org/), then in this repo run `cd scripts && npm install`. For PNG with local Mermaid, `pip install cairosvg` (and system Cairo if needed). Without cairosvg, local Mermaid still does SVG; PNG falls back to Kroki.
   - **SVG preview in node**: `pip install cairosvg` (or `comfyui-uml[svg-preview]`) gives real image preview for SVG; otherwise the IMAGE slot is a placeholder and you can open the saved file or use the viewer.
   - **Dynamic widget visibility**: `pip install comfy-dynamic-widgets` or `pip install comfyui-uml[dynamic-widgets]` so **kroki_url** / **diagram_options** show only for backend **web**, and **theme** only for **local**. Requires `web/js/` (created automatically).

## Updating

- **Restart required**: After updating (ComfyUI-Manager, git pull, or manual), **restart ComfyUI** so new nodes and web assets load.
- **Other nodes failing**: If Manager reports “Failed to update” for another node, that’s independent of ComfyUI-UML; retry or update that node manually, then restart ComfyUI.

## Usage

- Add the **UML Render (Mermaid/PlantUML/etc)** node (category: UML).
- Choose **backend**: `web` (Kroki API) or `local` (local Mermaid when diagram type is Mermaid, else web).
- Choose **diagram_type** and enter **code**. **output_format**: `png`, `svg`, `jpeg`, `pdf`, `txt`, or `base64` (validated per type). **diagram_options** (optional): JSON for Kroki, e.g. GraphViz `{"scale": 1.5}`, BlockDiag `{"antialias": ""}`, D2/PlantUML `{"theme": "dark"}`. See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).

### Kroki diagram types and format support

Supported formats per diagram type (matches [Kroki's support](https://docs.kroki.io/kroki/diagram-types)):

| Diagram type | png | svg | jpeg | pdf | txt | base64 |
|--------------|-----|-----|------|-----|-----|--------|
| actdiag | ✓ | ✓ | — | ✓ | — | — |
| blockdiag | ✓ | ✓ | — | ✓ | — | — |
| bpmn | — | ✓ | — | — | — | — |
| bytefield | — | ✓ | — | — | — | — |
| c4plantuml | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| d2 | ✓ | ✓ | — | — | — | — |
| dbml | — | ✓ | — | — | — | — |
| ditaa | ✓ | ✓ | — | — | — | — |
| erd | ✓ | ✓ | ✓ | ✓ | — | — |
| excalidraw | — | ✓ | — | — | — | — |
| graphviz | ✓ | ✓ | ✓ | ✓ | — | — |
| mermaid | ✓ | ✓ | — | — | — | — |
| nomnoml | — | ✓ | — | — | — | — |
| nwdiag | ✓ | ✓ | — | ✓ | — | — |
| packetdiag | ✓ | ✓ | — | ✓ | — | — |
| pikchr | — | ✓ | — | — | — | — |
| plantuml | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| rackdiag | ✓ | ✓ | — | ✓ | — | — |
| seqdiag | ✓ | ✓ | — | ✓ | — | — |
| structurizr | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| svgbob | — | ✓ | — | — | — | — |
| symbolator | — | ✓ | — | — | — | — |
| tikz | ✓ | ✓ | ✓ | ✓ | — | — |
| umlet | ✓ | ✓ | ✓ | — | — | — |
| vega | ✓ | ✓ | — | ✓ | — | — |
| vegalite | ✓ | ✓ | — | ✓ | — | — |
| wavedrom | — | ✓ | — | — | — | — |
| wireviz | ✓ | ✓ | — | — | — | — |

(✓ = supported, — = not supported for that type.)

**Outputs** (full list):

- **IMAGE**: Rendered diagram for png, jpeg, and svg (when cairosvg is installed); placeholder for pdf, txt, base64 (file still saved).
- **path**: File path under ComfyUI output directory, `uml/` subfolder; extension matches format.
- **kroki_url**: Shareable Kroki GET URL; open in browser or right-click node → **Open in viewer**.
- **content_for_viewer**: For **svg**, raw SVG string (for ComfyUI_Viewer); otherwise the saved file path.

### Opening the diagram in the viewer

1. **From the node**: Right-click the UML node → **Open in viewer** (uses current diagram code).
2. **Manual URL**: Copy **kroki_url** and open `http://localhost:8188/extensions/ComfyUI-UML/viewer.html?url=<paste_kroki_url>`. Data URLs supported: `?url=data:image/svg+xml;base64,...`.
3. Toolbar: zoom (Fit, 100%, ±), **Save locally**, **Save to ComfyUI**, Copy link.

### LLM + Prompt Engine workflow

1. **LLM Prompt Engine** (category UML): Builds a prompt from a template and positive/negative instructions; placeholders `{{description}}`, `{{diagram_type}}`, `{{format}}`; **template_file** loads presets from `prompts/` (e.g. `kroki_logo.txt`). Outputs: **prompt**, **positive**, **negative**.
2. **LLM Call (OpenAI/Anthropic)** (category UML): Sends **prompt** (and optionally **negative_prompt**). Set **OPENAI_API_KEY** or **ANTHROPIC_API_KEY**, or pass **api_key** in the node. Output **text** → UML node **code_input**.
3. Connect **LLM Call** → **code_input**, set **diagram_type** and **output_format**, run to get diagram from LLM-generated code.

**Workflow**: Load **workflows/llm_kroki_logo.json** for Prompt Engine → LLM Call → UML Render. Set API key and run.

**Prompt files**: Add `.txt` under **prompts/** with three blocks separated by `---`: template, positive, negative. Use placeholders; **template_file** dropdown lists them.

## Testing

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Config: [comfy-test.toml](comfy-test.toml). Workflows under `workflows/` are executed; add new ones to `[test.workflows]` `cpu` in `comfy-test.toml`.

## Workflows

Included workflow files (load from ComfyUI or open the JSON):

- **uml_quickstart.json** — Mermaid, PlantUML, GraphViz, D2; PNG. Quick tryout.
- **uml_all_diagrams.json** — All 28 diagram types in a grouped layout.
- **uml_mermaid.json**, **uml_plantuml.json**, **uml_graphviz.json** — Single-node examples.
- **llm_kroki_logo.json** — LLM + Prompt Engine → Kroki; needs API key (see above).

**Loading workflows:** Prefer loading from the files in `workflows/` (e.g. **Load** → `workflows/llm_kroki_logo.json`) so the graph format is correct. If you see "Cannot convert undefined or null to object" or "KeyError: class_type", the workflow likely has a wrong format (e.g. from Manager cache or paste). See [Workflow format](web/docs/WorkflowFormat.md) and use `scripts/normalize_workflow.py` to fix broken JSON.

**Expected workflow format** (for compatibility with ComfyUI's loader and Queue Prompt):

- **links:** Array of objects `{id, origin_id, origin_slot, target_id, target_slot, type}`. No all-null entries.
- **groups:** Array of objects with `title`, `bound` (e.g. `[x, y, w, h]`), and `nodes`.
- **Root:** Use `lastNodeId` and `lastLinkId` (camelCase). Avoid graph payloads that use `last_node_id` / `last_link_id` with corrupted `links` or empty `groups`.

## License

MIT. See repository license.

## Author

**antoinebou12** — [GitHub](https://github.com/antoinebou12) · [Comfy Registry publisher](https://registry.comfy.org/publishers/antoinebou12)

## Publishing to the Comfy Registry

The workflow `.github/workflows/publish-node.yml` publishes when `pyproject.toml` changes on `main`/`master`. Add a repository secret:

1. Create a [personal access token](https://docs.comfy.org/registry/publishing) on the Comfy Registry for your publisher.
2. **Settings → Secrets and variables → Actions → New repository secret**: Name `REGISTRY_ACCESS_TOKEN`, Value your token.

Without it, the publish job fails with a clear message. "Failed to validate token" means the token must be for the publisher in `pyproject.toml` (`PublisherId`) and the Comfy Registry publisher must be linked to this repo.
