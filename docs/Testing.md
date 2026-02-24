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

**In-repo fix:** The ComfyUI-UML extension patches `app.graphToPrompt` so that its return value is normalized: every node in the prompt gets `class_type` set (from the current graph node, or `_meta`, or type) when missing. This runs in the same extension as the workflow load normalizer (`ComfyUI-UML.workflowNormalizer`). After loading the extension, comfy-test’s validation should see valid nodes. If you still see the error, ensure the ComfyUI-UML frontend script is loaded (check for `[ComfyUI-UML] graphToPrompt normalizer installed` in the browser console when opening ComfyUI).

**If failures persist:**

- Ensure the workflow under **workflows/** has valid nodes with `class_type` (e.g. use `scripts/generate_all_diagrams_workflow.py normalize`).
- This may be a ComfyUI frontend or comfy-test interaction issue. Consider reporting to [comfy-test issues](https://github.com/PozzettiAndrea/comfy-test/issues) with the error message and sample, and optionally to [ComfyUI](https://github.com/Comfy-Org/ComfyUI) (e.g. issues around "node missing class_type" such as #5409).
- If you find a ComfyUI or comfy-test version where this validation passes without the patch, document it here as a known-good combination.

## "Env: not installed (run comfy-env install)"

If ComfyUI Manager or comfy-env reports:

```text
ComfyUI-UML
✓ Config: root (...\ComfyUI-UML\comfy-env-root.toml)
✗ Env: not installed (run comfy-env install)
```

the plugin’s comfy-env environment has not been created yet. Do one of the following:

- **From the ComfyUI-UML folder:** run `python install.py`. If `comfy_env` is available it will run `comfy_env.install()`; otherwise it will use `uv sync` or `pip install -r requirements.txt`.
- **If you use the comfy-env CLI:** from your ComfyUI root run `comfy-env install` (or the command shown by your Env Manager) so the env for this node is created. To install **only** ComfyUI-UML’s env (e.g. portable Windows with embedded Python):
  ```bash
  .\python_embeded\python.exe -m comfy_env.cli install --dir ComfyUI\custom_nodes\ComfyUI-UML
  ```
  (Adjust `.\python_embeded\` if your Python lives elsewhere; `--dir` must point at the folder that contains `comfy-env-root.toml`.)
- **Without comfy-env:** set `COMFYUI_UML_SKIP_COMFY_ENV=1` and install dependencies with `pip install -r requirements.txt` or `uv sync` from the plugin root.

After the env is installed, restart ComfyUI and the message should disappear.

## "Install these nodes" / "Installer broken" (UMLDiagram, UMLViewerURL)

If ComfyUI says the workflow uses custom nodes you haven’t installed (UMLDiagram, UMLViewerURL) and the in-app **Install** button fails or shows "Installer broken":

1. **Install from the plugin folder:** Open a terminal in `ComfyUI-UML` (e.g. `custom_nodes\ComfyUI-UML`) and run:
   ```bash
   python install.py
   ```
   Exit code 0 means success; then restart ComfyUI.
2. **If you use comfy-env:** Run the env install first (see **"Env: not installed"** above), then restart ComfyUI.
3. **Skip comfy-env:** Set `COMFYUI_UML_SKIP_COMFY_ENV=1`, run `pip install -r requirements.txt` (or `uv sync`) in the plugin folder, then restart ComfyUI.

The plugin’s `install()` no longer calls `sys.exit()` when invoked at load time, so a failed pip/uv step will not crash ComfyUI; only when you run `python install.py` directly does it exit non-zero on failure so Manager can detect install errors. If `comfy_env.install()` or the local install raises an exception at load time, it is caught and logged (e.g. `ComfyUI-UML: comfy_env install failed (nodes will still load): ...`); node registration continues so UMLDiagram and UMLViewerURL still appear.

## "Node 'UMLDiagram' not found" when queueing a prompt

If you see:

```text
Node 'UMLDiagram' not found. The custom node may not be installed.: Node ID '#1'
invalid prompt: {'type': 'missing_node_type', 'message': "Node 'UMLDiagram' not found. The custom node may not be installed.", ...}
```

**Cause:** ComfyUI-UML is loaded at startup (it appears in the import list), but prompt execution or validation runs in a **different context** that does not have our nodes registered. This often happens when **comfy-env** (ComfyUI-Env-Manager) is installed and uses **node isolation**: only a subset of nodes (e.g. "17 nodes" in the isolation root) are available to the worker that executes prompts. If ComfyUI-UML is not in that subset, the executor reports "UMLDiagram" not found.

**What to do:**

- **If you use comfy-env / ComfyUI-Env-Manager:** Ensure ComfyUI-UML is included in the set of nodes that are available to the default execution environment (e.g. add ComfyUI-UML to the isolation root or to the list of nodes that run in the main process). Check the Env Manager or comfy-env documentation for how to include a custom node in the execution context.
- **Skip comfy-env for this extension:** Set the environment variable `COMFYUI_UML_SKIP_COMFY_ENV=1` before starting ComfyUI (e.g. in your launcher or shell). ComfyUI-UML will not call `comfy_env.install()`, so it will not participate in comfy-env’s isolation and its nodes should remain available in the main process.
- **Temporary test:** In ComfyUI-UML’s `__init__.py`, comment out or remove the `comfy_env` block (the `try: from comfy_env import install; install(); except ImportError: pass`). Restart ComfyUI and queue the workflow again. If the error goes away, the issue is comfy-env configuration; add ComfyUI-UML to the execution context or use `COMFYUI_UML_SKIP_COMFY_ENV=1` instead of leaving the block commented out long term.
- Ensure no other code is replacing or filtering `NODE_CLASS_MAPPINGS` so that `UMLDiagram` remains registered in the process that runs your workflow.
