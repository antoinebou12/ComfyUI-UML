# Testing

## Comfy-test

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Workflows under `workflows/` are executed according to the config.

## Config: comfy-test.toml

The root file [comfy-test.toml](../comfy-test.toml) controls how tests run:

- **[test]** — `levels`: test levels from `syntax` through `install`, `registration`, `instantiation`, `execution`. `publish = true` enables publish checks.
- **[test.workflows]** — `timeout`: max seconds per workflow (default 300). `cpu`: list of workflow JSON filenames (under `workflows/`) to run on CPU. ComfyUI-UML uses diagram-only workflows (`uml_<type>_cpu.json`) so graphToPrompt validation passes; regenerate with `python scripts/generate_all_diagrams_workflow.py generate-cpu`.
- The suite runs only diagram-only workflows (Kroki/base64 URL rendering). LLM workflows are not included.
- **[test.platforms]** — which OSes to run on (linux, macos, windows, windows_portable).

## Adding workflows to the test suite

1. For **CPU execution tests**, use diagram-only workflows (`workflows/uml_<type>_cpu.json`). Regenerate the full set with:

   ```bash
   python scripts/generate_all_diagrams_workflow.py generate-cpu
   ```

   The `cpu` list in **comfy-test.toml** and **pyproject.toml** should reference these `*_cpu.json` filenames so comfy-test validation (graphToPrompt) passes.

2. To add a new diagram type to the CPU tests: after adding the type in `nodes/kroki_client.py`, run `generate-cpu` again (it writes one `uml_<type>_cpu.json` per type), then add the new filename to the `cpu` array in both config files.

3. For reference, to add any other workflow to the suite: put the JSON under **workflows/** and add its filename to the **cpu** array in **comfy-test.toml** and **pyproject.toml**.

## Running comfy-test locally

If you have [comfy-test](https://github.com/PozzettiAndrea/comfy-test) installed, you can run it from the ComfyUI-UML repo root (or from your ComfyUI install with this node in `custom_nodes/`). See the comfy-test repo for the exact CLI and environment setup.

## Known issue: graphToPrompt validation failures

Some workflow runs may fail with:

```text
Validation failed: graphToPrompt produced nodes without class_type: graphToPrompt: 1 nodes, missing class_type: [1], sample: {"inputs":{"UNKNOWN":0},"_meta":{}}
```

**Cause:** comfy-test validates the graph by calling ComfyUI's in-browser `graphToPrompt()` after loading the workflow. That conversion sometimes emits a node without a `class_type` field (e.g. `inputs` as `{"UNKNOWN":0}`). The **input** workflow JSON from this repo is valid (every node has `class_type`); the failure is in the **produced** API-format graph from the frontend.

**What to do:**

- Regenerate CPU workflows so they match the generator: `python scripts/generate_all_diagrams_workflow.py generate-cpu`.
- If failures persist, this is likely a ComfyUI frontend or comfy-test interaction issue. Consider reporting to [comfy-test issues](https://github.com/PozzettiAndrea/comfy-test/issues) with the error message and sample, and optionally to [ComfyUI](https://github.com/Comfy-Org/ComfyUI) (e.g. issues around "node missing class_type" such as #5409).
- If you find a ComfyUI or comfy-test version where this validation passes, document it here as a known-good combination.
