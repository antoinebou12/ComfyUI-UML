# Testing

## Comfy-test

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Workflows under `workflows/` are executed according to the config.

## Config: comfy-test.toml

The root file [comfy-test.toml](../comfy-test.toml) controls how tests run:

- **[test]** — `levels`: test levels from `syntax` through `install`, `registration`, `instantiation`, `execution`. `publish = true` enables publish checks.
- **[test.workflows]** — `timeout`: max seconds per workflow (default 300). `cpu`: list of workflow JSON filenames (under `workflows/`) to run on CPU. ComfyUI-UML uses diagram-only workflows (`uml_<type>_cpu.json`) so graphToPrompt validation passes; regenerate with `python scripts/generate_all_diagrams_workflow.py generate-cpu`.
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
