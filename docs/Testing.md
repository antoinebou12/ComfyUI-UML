# Testing

## Comfy-test

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Workflows under `workflows/` are executed according to the config.

## Config: comfy-test.toml

The root file [comfy-test.toml](../comfy-test.toml) controls how tests run:

- **[test]** — `levels`: test levels from `syntax` through `install`, `registration`, `instantiation`, `execution`. `publish = true` enables publish checks.
- **[test.workflows]** — `timeout`: max seconds per workflow (default 300). `cpu`: list of workflow JSON filenames (under `workflows/`) to run on CPU. ComfyUI-UML uses a single **diagram-only** workflow (`uml_single_diagram_only.json`) for execution tests: one UMLDiagram node, no links. This avoids graphToPrompt link validation issues (e.g. `InvalidLinkError: No link found in parent graph` on macOS) when the frontend converts the graph.
- The suite runs only diagram-only workflows (Kroki/base64 URL rendering). LLM workflows are not included.
- **[test.platforms]** — which OSes to run on (linux, macos, windows, windows_portable).

## Adding workflows to the test suite

1. Add the workflow JSON under **workflows/** and add its filename to the **cpu** array in **comfy-test.toml** and **pyproject.toml**. The default suite uses **uml_single_diagram_only.json** (one UMLDiagram, no links, no groups).

## Running comfy-test locally

If you have [comfy-test](https://github.com/PozzettiAndrea/comfy-test) installed, you can run it from the ComfyUI-UML repo root (or from your ComfyUI install with this node in `custom_nodes/`). See the comfy-test repo for the exact CLI and environment setup.

## Known issue: graphToPrompt validation failures

Some workflow runs may fail with:

```text
Validation failed: graphToPrompt produced nodes without class_type: graphToPrompt: 1 nodes, missing class_type: [1], sample: {"inputs":{"UNKNOWN":0},"_meta":{}}
```

**Cause:** comfy-test validates the graph by calling ComfyUI's in-browser `graphToPrompt()` after loading the workflow. That conversion sometimes emits a node without a `class_type` field (e.g. `inputs` as `{"UNKNOWN":0}`). The **input** workflow JSON from this repo is valid (every node has `class_type`); the failure is in the **produced** API-format graph from the frontend.

**What to do:**

- Ensure the workflow under **workflows/** has valid nodes with `class_type` (e.g. use `scripts/generate_all_diagrams_workflow.py normalize`).
- If failures persist, this is likely a ComfyUI frontend or comfy-test interaction issue. Consider reporting to [comfy-test issues](https://github.com/PozzettiAndrea/comfy-test/issues) with the error message and sample, and optionally to [ComfyUI](https://github.com/Comfy-Org/ComfyUI) (e.g. issues around "node missing class_type" such as #5409).
- If you find a ComfyUI or comfy-test version where this validation passes, document it here as a known-good combination.
