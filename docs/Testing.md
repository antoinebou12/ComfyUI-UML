# Testing

## Comfy-test

CI runs [comfy-test](https://github.com/PozzettiAndrea/comfy-test) on push/PR to `main`. Workflows under `workflows/` are executed according to the config.

## Config: comfy-test.toml

The root file [comfy-test.toml](../comfy-test.toml) controls how tests run:

- **[test]** — `levels`: test levels from `syntax` through `install`, `registration`, `instantiation`, `execution`. `publish = true` enables publish checks.
- **[test.workflows]** — `timeout`: max seconds per workflow (default 300). `cpu`: list of workflow JSON filenames (under `workflows/`) to run on CPU.
- **[test.platforms]** — which OSes to run on (linux, macos, windows, windows_portable).

## Adding workflows to the test suite

1. Put the workflow JSON under **workflows/** (e.g. `workflows/my_workflow.json`).
2. Add the filename to the **cpu** array in **comfy-test.toml**:

   ```toml
   [test.workflows]
   timeout = 300
   cpu = ["uml_mermaid.json", "uml_plantuml.json", "uml_graphviz.json", "my_workflow.json"]
   ```

3. Push; CI will run the new workflow in the comfy-test pipeline.

## Running comfy-test locally

If you have [comfy-test](https://github.com/PozzettiAndrea/comfy-test) installed, you can run it from the ComfyUI-UML repo root (or from your ComfyUI install with this node in `custom_nodes/`). See the comfy-test repo for the exact CLI and environment setup.
