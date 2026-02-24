# Workflows

## Included workflow files

Load from ComfyUI (**Load** → choose file) or open the JSON:

- **uml_quickstart.json** — Mermaid, PlantUML, GraphViz, D2; PNG. Quick tryout.
- **uml_all_diagrams.json** — All 28 diagram types in a grouped layout.
- **uml_mermaid.json**, **uml_plantuml.json**, **uml_graphviz.json** — Single-node examples.
- **llm_kroki_logo.json** — LLM + Prompt Engine → Kroki; needs API key (see [Usage](Usage.md)).

## Loading workflows

Prefer loading from the files in **workflows/** (e.g. **Load** → `workflows/llm_kroki_logo.json`) so the graph format is correct. When you load from a file, the ComfyUI-UML extension normalizes the workflow in the browser; when you load from Manager cache, a URL, or a paste, use `scripts/generate_all_diagrams_workflow.py normalize` (see below).

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
python scripts/generate_all_diagrams_workflow.py normalize workflows/llm_kroki_logo.json -o fixed.json
# Or stdin
python scripts/generate_all_diagrams_workflow.py normalize - < broken.json > fixed.json
```

The script rebuilds `links` from node inputs/outputs if missing or corrupted, ensures every group has a valid `bound`, and normalizes root keys to camelCase.
