# Workflow format (ComfyUI graph JSON)

Workflows shipped in `workflows/` and `example_workflows/` use a format that ComfyUI's frontend can load and convert correctly when you **Queue Prompt**. If you load a workflow from Manager cache, a URL, or a paste and see errors like "Cannot convert undefined or null to object", **"KeyError: class_type"**, or **"SyntaxError: Unexpected non-whitespace character after JSON"** when queueing, the JSON is likely in a different or corrupted format (e.g. snake_case `last_node_id` instead of camelCase `lastNodeId`, or wrong link structure).

When you **Load** a workflow from a file in ComfyUI, the ComfyUI-UML extension runs an in-browser normalizer that fixes camelCase, links, and group bounds. For workflows loaded from Manager, a URL, or a paste (where that normalizer may not run), use the `scripts/generate_all_diagrams_workflow.py normalize` command below to repair the file first.

## Expected structure

- **links:** Array of **objects**, one per link:
  - `id`, `origin_id`, `origin_slot`, `target_id`, `target_slot`, `type`
  - Example: `{"id": 1, "origin_id": 1, "origin_slot": 0, "target_id": 2, "target_slot": 0, "type": "STRING"}`
  - Do **not** use array-style links (e.g. `[id, origin, origin_slot, target, target_slot, type]`) and never leave entries as all-null (e.g. `[null,null,null,null,null,null]`).

- **groups:** Array of objects, each with:
  - `title`: string
  - `bound`: array of four numbers `[x, y, w, h]` (or equivalent). The frontend uses this for the group rectangle; missing or invalid `bound` can cause load errors.
  - `nodes`: array of node IDs in the group

- **Root keys:** Prefer camelCase for compatibility:
  - `lastNodeId`, `lastLinkId` (not `last_node_id`, `last_link_id`).
  - Other keys (`nodes`, `links`, `groups`, `config`, `extra`, `version`) unchanged.

## Fixing broken workflows

Use `scripts/generate_all_diagrams_workflow.py normalize` to repair a workflow file (e.g. after pasting from the browser or loading from a bad source):

```bash
# From the ComfyUI-UML repo root
python scripts/generate_all_diagrams_workflow.py normalize workflows/llm_kroki_logo.json -o fixed.json
# Or stdin
python scripts/generate_all_diagrams_workflow.py normalize - < broken.json > fixed.json
```

The script rebuilds `links` from node inputs/outputs if they are missing or corrupted, ensures every group has a valid `bound`, and normalizes root keys to camelCase.

## See also

- [Workflows](Workflows.md) — workflow list, loading tips, and normalize script usage.
