# ComfyUI-UML

ComfyUI custom nodes for rendering diagrams (Mermaid, PlantUML, Graphviz, etc.) via [Kroki](https://kroki.io) or local renderers.

## Features

- **Kroki (web)**: Many diagram types via the Kroki API. No local setup.
- **Local Mermaid**: When backend is "local" and diagram type is Mermaid, uses [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) for offline, themeable SVG/PNG.
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

## Usage

- Add the **UML Render (Mermaid/PlantUML/etc)** node (category: UML).
- Choose **backend**: `web` (Kroki API) or `local` (uses local Mermaid when diagram type is Mermaid, else falls back to web).
- Choose **diagram_type** (e.g. mermaid, plantuml, graphviz) and enter your diagram **code**.
- **theme** (optional): When backend is local and type is Mermaid, pick a beautiful-mermaid theme (e.g. tokyo-night, catppuccin-mocha).

Output is saved under ComfyUI’s output directory in a `uml` subfolder and returned as IMAGE (for PNG) plus the file path.

## License

See repository license.
