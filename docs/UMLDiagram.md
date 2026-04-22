# UML Render (Mermaid/PlantUML/etc)

Renders diagram source (Mermaid, PlantUML, Graphviz, D2, and 28+ types) to an image and saves the file via [Kroki](https://kroki.io) or local renderers.

## Parameters

- **backend**: `web` (Kroki API) or `local` (local Mermaid when diagram type is Mermaid; otherwise falls back to web).
- **kroki_url**: Kroki server URL when backend is web (default: `https://kroki.io`).
- **diagram_type**: One of the supported **Kroki** diagram types (URL path segment), e.g. `mermaid`, `plantuml`, `graphviz`, `d2`. This is **not** the same namespace as [uml-mcp](https://github.com/antoinebou12/uml-mcp) **`generate_uml`**, which uses **logical** types (`class`, `sequence`, `activity`, …) and maps them to Kroki backends internally. In ComfyUI-UML you pick the **backend** name that matches your source. See **`uml://types`** in uml-mcp for how logical types map to backends when authoring for agents; here, match **diagram_type** to the Kroki list in [KrokiFormats.md](KrokiFormats.md).
- **code**: Diagram source text. When **code_input** is connected, it overrides this widget (e.g. from an LLM node).
- **output_format**: `png`, `svg`, `jpeg`, `pdf`, `txt`, or `base64`. Not every format is supported by every diagram type; the node validates against Kroki. PNG and JPEG produce a ComfyUI IMAGE; other formats are saved to disk and the IMAGE output is a placeholder.
- **diagram_options**: Optional JSON passed to Kroki (e.g. `{"scale": 1.5}` for GraphViz, `{"theme": "dark"}` for D2/PlantUML). See [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/).
- **theme**: For local Mermaid only; theme name (e.g. `tokyo-night`, `catppuccin-mocha`).

## Outputs

- **IMAGE**: Rendered diagram for png, jpeg, and svg (when cairosvg is installed); placeholder for pdf/txt/base64.
- **path**: File path under ComfyUI output directory, `output/uml/` subfolder.
- **kroki_url**: Shareable Kroki GET URL. Right-click node → **Open in viewer** to open in the built-in viewer.
- **content_for_viewer**: When format is svg, the raw SVG string (connect to ComfyUI_Viewer for in-UI display). Otherwise the saved file path.

## Usage

1. Add the node (category: UML), set **diagram_type** and **code** (or connect **code_input** from an LLM).
2. Choose **output_format**; the UI restricts options per diagram type.
3. Right-click the node → **Open in viewer** to open the diagram in the zoomable viewer (Save to ComfyUI writes to `output/uml/`).

## See also

- [Kroki diagram types and format support](KrokiFormats.md)
- [Kroki diagram options](https://docs.kroki.io/kroki/setup/diagram-options/)
- [uml-mcp](https://github.com/antoinebou12/uml-mcp) — MCP server with logical `diagram_type` keys and `uml://types` / `generate_uml` for agent workflows outside ComfyUI.
