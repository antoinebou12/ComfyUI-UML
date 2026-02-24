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
- [Testing](#testing)
- [Workflows](#workflows)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Author](#author)
- [Publishing](#publishing-to-the-comfy-registry)

**Documentation:** [docs/](docs/) — usage, Kroki formats, workflows, testing, publishing, node reference.

## Features

- **Kroki (web)**: Many diagram types via the Kroki API. No local setup.
- **28 Kroki diagram types** and **output formats** (png, svg, jpeg, pdf, txt, base64) per type; validated against [Kroki's support matrix](https://docs.kroki.io/kroki/diagram-types).
- **Diagram options**: Optional JSON for quality/theme (e.g. GraphViz scale, Mermaid/PlantUML/D2 theme). See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).
- **Shareable Kroki URL** and **built-in viewer** (zoom, Save to ComfyUI, copy link).
- **ComfyUI_Viewer**: Connect **content_for_viewer** for SVG in iframe; other formats use saved path.
- **Local Mermaid**: Backend "local" + [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) for offline SVG/PNG; optional theme.
- **Local Graphviz**: Optional when the `graphviz` Python package is installed.

See [docs/Usage.md](docs/Usage.md) and [docs/KrokiFormats.md](docs/KrokiFormats.md) for details.

## Installation

1. Clone or copy this folder into `ComfyUI/custom_nodes/`.
2. Install dependencies: `pip install -r requirements.txt` or `uv sync`.
3. **Optional** — Local Mermaid: Node.js + `cd scripts && npm install`. PNG: `pip install cairosvg`. SVG preview in node: `pip install cairosvg`. Dynamic widget visibility: `pip install comfy-dynamic-widgets` (or extras from pyproject.toml).

## Updating

After updating (Manager, git pull, or manual), **restart ComfyUI** so nodes and web assets load. Other nodes failing to update are independent; retry that node and restart.

## Usage

Add the **UML Render (Mermaid/PlantUML/etc)** node (category: UML). Choose **backend** (web/local), **diagram_type**, enter **code**, and set **output_format** (png, svg, jpeg, pdf, txt, base64 — validated per type). Optional **diagram_options** JSON for Kroki.

Full usage, outputs, viewer, and LLM workflow: [docs/Usage.md](docs/Usage.md). Diagram type × format table: [docs/KrokiFormats.md](docs/KrokiFormats.md).

## Testing

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. See [docs/Testing.md](docs/Testing.md) for config ([comfy-test.toml](comfy-test.toml)) and adding workflows.

## Workflows

- **uml_quickstart.json** — Mermaid, PlantUML, GraphViz, D2; quick tryout.
- **uml_all_diagrams.json** — All 28 diagram types.
- **uml_mermaid.json**, **uml_plantuml.json**, **uml_graphviz.json** — Single-node examples.
- **llm_kroki_logo.json** — LLM + Prompt Engine → Kroki (needs API key).

Full list, loading tips, and format: [docs/Workflows.md](docs/Workflows.md). Workflow format and normalizer: [docs/WorkflowFormat.md](docs/WorkflowFormat.md).

## Troubleshooting

- **"Missing nodes" / UMLDiagram not found** — Restart ComfyUI after installing or updating. Load a workflow from this repo's `workflows/` folder (e.g. **Load** → `workflows/uml_plantuml.json`) instead of from Manager cache or paste.
- **KeyError: class_type**, **"SyntaxError: Unexpected non-whitespace character after JSON at position 4"**, or other JSON/prompt errors when queueing — The workflow graph format may be wrong or the frontend sent the wrong payload. Load from `workflows/` (e.g. `uml_quickstart.json`, `uml_plantuml.json`) or fix the file with the normalizer script (see [docs/WorkflowFormat.md](docs/WorkflowFormat.md)).
- **"Cannot convert undefined or null to object" when loading** — Load the workflow from the `workflows/` folder so the in-browser normalizer runs, or fix the JSON with `scripts/generate_all_diagrams_workflow.py normalize` (see [docs/WorkflowFormat.md](docs/WorkflowFormat.md)).

## License

MIT. See repository license.

## Author

**antoinebou12** — [GitHub](https://github.com/antoinebou12) · [Comfy Registry publisher](https://registry.comfy.org/publishers/antoinebou12)

## Publishing to the Comfy Registry

Publishing runs when `pyproject.toml` changes on `main`/`master`. See [docs/Publishing.md](docs/Publishing.md) for token setup and troubleshooting.
