# Workflow format (ComfyUI graph JSON)

Workflows shipped in `workflows/` and `example_workflows/` use a format that ComfyUI's frontend can load and convert correctly when you **Queue Prompt**. If you load a workflow from Manager cache, a URL, or a paste and see errors like "Cannot convert undefined or null to object" or "KeyError: class_type", the JSON is likely in a different or corrupted format.

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

Use the normalizer script to repair a workflow file (e.g. after pasting from the browser or loading from a bad source):

```bash
# From the ComfyUI-UML repo root
python scripts/normalize_workflow.py workflows/llm_kroki_logo.json -o fixed.json
# Or stdin
python scripts/normalize_workflow.py - < broken.json > fixed.json
```

The script rebuilds `links` from node inputs/outputs if they are missing or corrupted, ensures every group has a valid `bound`, and normalizes root keys to camelCase.

## See also

- [README – Workflows](../README.md#workflows)
- Plan: Fix ComfyUI workflow load and execution errors (Rectangle.set, KeyError class_type, JSON / missing nodes)
