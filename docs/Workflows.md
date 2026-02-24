# Workflows

## Included workflow files

Load from ComfyUI (**Load** → choose file) or open the JSON:

- **uml_single_diagram_only.json** — One UMLDiagram node, no links. Used for CI execution tests.
- **uml_single_node.json** — Minimal workflow: one UMLDiagram node plus UMLViewerURL (kroki_url only). No groups; easy to test and load.
- **uml_mermaid.json** — One UMLDiagram (Mermaid) plus UMLViewerURL (kroki_url only). Example per diagram type.
- **uml_plantuml.json** — One UMLDiagram (PlantUML) plus UMLViewerURL (kroki_url only).
- **uml_llm_ollama.json** — LLM (Ollama) → Kroki: LLMPromptEngine → LLMCall → UMLDiagram → UMLViewerURL.

## Loading workflows

Prefer loading from the files in **workflows/** (e.g. **Load** → `workflows/uml_single_node.json`) so the graph format is correct. When you load from a file, the ComfyUI-UML extension normalizes the workflow in the browser; when you load from Manager cache, a URL, or a paste, use `scripts/generate_all_diagrams_workflow.py normalize` (see below).

If you see **"This workflow has missing nodes"** (UMLDiagram, UMLViewerURL), the ComfyUI-UML custom node is not installed or failed to register in that ComfyUI instance. Install ComfyUI-UML, restart ComfyUI, then load workflows from the `workflows/` folder.

If you see "Cannot convert undefined or null to object" or "KeyError: class_type", the workflow likely has a wrong format (e.g. from Manager cache or paste). See [WorkflowFormat.md](WorkflowFormat.md) and use `scripts/generate_all_diagrams_workflow.py normalize` (see below).

## Expected format (summary)

- **links:** Array of objects `{id, origin_id, origin_slot, target_id, target_slot, type}`. No all-null entries.
- **groups:** Array of objects with `title`, `bound` (e.g. `[x, y, w, h]`), and `nodes`.
- **Root:** Use `lastNodeId` and `lastLinkId` (camelCase). Avoid graph payloads that use `last_node_id` / `last_link_id` with corrupted `links` or empty `groups`.

Full details: [WorkflowFormat.md](WorkflowFormat.md).

## Fixing broken workflows

Use `scripts/generate_all_diagrams_workflow.py normalize` to repair a workflow file:

```bash
# From the ComfyUI-UML repo root
python scripts/generate_all_diagrams_workflow.py normalize workflows/uml_single_node.json -o fixed.json
# Or stdin
python scripts/generate_all_diagrams_workflow.py normalize - < broken.json > fixed.json
```

The script rebuilds `links` from node inputs/outputs if missing or corrupted, ensures every group has a valid `bound`, and normalizes root keys to camelCase.

## Regenerating workflow files

To regenerate all workflows, add UMLViewerURL nodes where missing, update the frontend format list from Python, and run the format check (from repo root):

```bash
python scripts/generate_all_diagrams_workflow.py
```

This runs: sync JS formats from Python → generate → normalize → add viewer → normalize → formats sync check. It exits with code 1 if the format lists are out of sync or if any diagram type is missing default code.

- **SUPPORTED_FORMATS (frontend):** The object in `web/ComfyUI-UML.js` is generated from `nodes/kroki_client.py`. Do not edit it by hand. Run `python scripts/generate_all_diagrams_workflow.py` or `python scripts/generate_all_diagrams_workflow.py sync-formats` to update it after changing diagram types or formats in `kroki_client.py`.
- **Default code:** Every diagram type in `nodes/kroki_client.py` must have a file `nodes/defaults/<type>.txt` with valid example source. The generate script fails if any type is missing its default file.

Use `python scripts/generate_all_diagrams_workflow.py generate` to only generate and normalize (no add-viewer, no sync check).

## CPU execution tests (comfy-test)

Comfy-test runs workflow execution against the `cpu` list in `comfy-test.toml` and `pyproject.toml`. The suite uses a single diagram-only workflow: **workflows/uml_single_diagram_only.json** (one UMLDiagram, no links). To add more workflows to the test suite, add JSON files under **workflows/** and append their filenames to the `cpu` array in both config files.
