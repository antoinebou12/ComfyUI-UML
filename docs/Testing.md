# Testing

## Run pytest locally

From the repository root (with [uv](https://docs.astral.sh/uv/) installed):

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Or with **pip**: `pip install -e ".[dev]"` then `pytest` and `ruff check .`.

Tests live under **`tests/`** (routes, URL helpers; no full ComfyUI install required).

The repo root **`conftest.py`** sets **`COMFYUI_UML_PYTEST=1`** so the ComfyUI plugin **`__init__.py`** skips loading the full node stack (torch/numpy) during pytest. You do not need to set this manually when using pytest from this repository.

For contributor and AI-agent workflow (verification commands, ordered checklist for risky changes, Context7 for deps), see **[AGENTS.md](../AGENTS.md)**.

## Pytest (this repository)

GitHub Actions runs **`uv sync --extra dev`**, **`ruff check`**, **`pytest`**, and **`npm ci`** in **`web/js`** on **push** and **pull_request** to **`main`** / **`master`** via [`.github/workflows/pytest.yml`](../.github/workflows/pytest.yml).

## Pytest (uml-mcp monorepo)

When **ComfyUI-UML** lives inside the **[uml-mcp](https://github.com/antoinebou12/uml-mcp)** repository, GitHub Actions runs **`pytest ComfyUI-UML/tests`** via [`.github/workflows/comfyui-uml.yml`](https://github.com/antoinebou12/uml-mcp/blob/main/.github/workflows/comfyui-uml.yml) on changes under **`ComfyUI-UML/`** or **`uml-skill/`** (and supports **workflow_dispatch** for manual runs). Agent-facing steps also live in **uml-skill** [`references/COMFYUI-TESTS.md`](https://github.com/antoinebou12/uml-mcp/blob/main/uml-skill/references/COMFYUI-TESTS.md).

## Comfy-test

[comfy-test](https://github.com/PozzettiAndrea/comfy-test) runs from [`.github/workflows/workflow-tests.yml`](../.github/workflows/workflow-tests.yml) on **push** and **pull_request** to **`main`** / **`master`**. CI uses all **seven** upstream levels (`syntax` through `execution`, including **`static_capture`** and **`validation`**); see the level table in the [comfy-test README](https://github.com/PozzettiAndrea/comfy-test#test-levels). The workflow job must not set **`env`** next to **`uses:`** (GitHub rejects that for reusable workflows). The comfy-test **`cpu`** list runs diagram workflows only; **`uml_llm_ollama.json`** is not included. When you run LLM nodes in **GitHub Actions**, **`use_mock_llm()`** in `nodes/uml_llm_shared.py` returns true when **`GITHUB_ACTIONS`** is set unless **`COMFY_UI_UML_MOCK_LLM`** is explicitly **`0`**, **`false`**, or **`no`**. Workflow JSON files under **`workflows/`** listed in the config are executed in CI.

This repository standardizes on **Python 3.12** (see **`nodes/comfy-env.toml`**, **pytest** / **CodeQL** workflows, and **`act-comfy-test-linux.yml`**). Do not pin **`comfy-env.toml`** **`python`** to a version **newer** than [comfy-test](https://github.com/PozzettiAndrea/comfy-test)’s matrix **`actions/setup-python`** in its **`_test-*.yml`** files, or the comfy-test **install** level fails before ComfyUI starts.

## Config: comfy-test.toml

The root file [comfy-test.toml](../comfy-test.toml) controls how tests run:

- **[test]** — `levels`: ordered comfy-test stages: **`syntax`**, **`install`**, **`registration`**, **`instantiation`**, **`static_capture`**, **`validation`**, **`execution`** (see [comfy-test README](https://github.com/PozzettiAndrea/comfy-test#test-levels)). `publish = true` enables publish checks.
- **[test.workflows]** — `timeout`: max seconds per workflow (default 300). `cpu`: list of workflow JSON filenames (under `workflows/`) to run on CPU. The suite runs diagram-only and diagram+viewer examples (Mermaid, PlantUML); **`uml_llm_ollama.json`** is kept in **`workflows/`** for manual loads only (see below).
- **[test.platforms]** — which OSes to run on (linux, macos, windows, windows_portable).

## Adding workflows to the test suite

1. Add the workflow JSON under **workflows/** and add its filename to the **cpu** array in **comfy-test.toml** and **pyproject.toml**. The default suite is: **uml_single_diagram_only.json**, **uml_single_node.json**, **uml_mermaid.json**, **uml_plantuml.json**.

## Mock LLM (optional `uml_llm_ollama.json`)

**uml_llm_ollama.json** is not run by comfy-test in CI. When you load it (or other LLM graphs) in **GitHub Actions**, **LLMCall** and **UML Code Assistant** use the mock unless **`COMFY_UI_UML_MOCK_LLM`** is set to **`0`**, **`false`**, or **`no`**. Locally, set **`COMFY_UI_UML_MOCK_LLM=1`** (or **`true`**) before ComfyUI to force the mock. The fixed snippet is **`MOCK_LLM_RESPONSE`** in `nodes/uml_llm_shared.py`.

## Running comfy-test locally

If you have [comfy-test](https://github.com/PozzettiAndrea/comfy-test) installed, you can run it from the ComfyUI-UML repo root (or from your ComfyUI install with this node in `custom_nodes/`). See the comfy-test repo for the exact CLI and environment setup.

## Local act (nektos/act)

[`.github/workflows/workflow-tests.yml`](../.github/workflows/workflow-tests.yml) calls the external reusable **comfy-test** matrix, which then uses nested `uses: ./.github/workflows/_test-*.yml` paths **inside** that repository. **act** resolves those relative paths under **this** repo, so the full matrix workflow **cannot** be replayed locally with `act`.

Use [`.github/workflows/act-comfy-test-linux.yml`](../.github/workflows/act-comfy-test-linux.yml) instead (**`workflow_dispatch` only**): it inlines a single Linux job (venv, ComfyUI clone, Playwright, server, `comfy_test run`). The workflow pins **Python 3.12**; **`ghcr.io/catthehacker/ubuntu:act-22.04`** matches the usual **setup-python** manylinux toolchain for that release.

From the repo root, with Docker running:

```powershell
act workflow_dispatch -W .github/workflows/act-comfy-test-linux.yml -j linux-test -P "ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-22.04"
```

On **PowerShell**, `act` may emit info lines to **stderr**, which can surface as `NativeCommandError` even when the job continues; that is cosmetic. You can use `$ErrorActionPreference = 'Continue'` for the session if the noise is distracting.

## "Prompt has no outputs" (comfy-test validation)

ComfyUI’s **`validate_prompt`** treats a workflow as runnable only if at least one node in the API prompt has **`OUTPUT_NODE = True`** on its Python class (same rule as the desktop app). **`UMLDiagram`** and **`UMLViewerURL`** therefore set **`OUTPUT_NODE = True`** so diagram-only and diagram→viewer graphs validate and execute under comfy-test.

Separately, comfy-test converts litegraph JSON to API format with **`WorkflowConverter`**: nodes with **no connected outputs** can be dropped unless **`object_info`** marks them as output nodes. **`uml_single_diagram_only.json`** wires **`UMLDiagram.IMAGE`** into the built-in **`PreviewImage`** node so the converter always keeps **`UMLDiagram`** in the prompt. Regenerate that file with **`scripts/generate_all_diagrams_workflow.py`** (`build_uml_single_diagram_only_workflow`) after changing the pattern.

## Known issue: graphToPrompt validation failures

Some workflow runs may fail with:

```text
Validation failed: graphToPrompt produced nodes without class_type: graphToPrompt: 1 nodes, missing class_type: [1], sample: {"inputs":{"UNKNOWN":0},"_meta":{}}
```

**Cause:** comfy-test validates the graph by calling ComfyUI's in-browser `graphToPrompt()` after loading the workflow. That conversion sometimes emits a node without a `class_type` field (e.g. `inputs` as `{"UNKNOWN":0}`). The **input** workflow JSON from this repo is valid (every node has `class_type`); the failure is in the **produced** API-format graph from the frontend.

**In-repo fix:** The ComfyUI-UML extension patches `app.graphToPrompt` so that its return value is normalized: every node in the prompt gets `class_type` set (from the current graph node, or `_meta`, or type) when missing. This runs in the same extension as the workflow load normalizer (`ComfyUI-UML.workflowNormalizer`). After loading the extension, comfy-test’s validation should see valid nodes. If you still see the error, ensure the ComfyUI-UML frontend script is loaded (check for `[ComfyUI-UML] graphToPrompt normalizer installed` in the browser console when opening ComfyUI).

**Missing upstream node (`KeyError`):** Some runs fail with `Prompt outputs failed validation` / `exception_during_validation` and a **`KeyError`** in ComfyUI `validate_prompt` (e.g. `prompt[o_id]['class_type']`) on **`UMLDiagram`** while the console still shows **`graphToPrompt: N nodes, missing class_type: []`**. That means **`graphToPrompt`** omitted an upstream id (often node **`1`** in **`uml_llm_ollama.json`**, **`UMLLLMCodeGenerator`**) but left **`[upstream_id, slot]`** wire tuples in **`code_input`**. The same extension pass merges those missing origins from the live LiteGraph into the API prompt map until the wire closure is complete (`_mergeMissingUpstreamNodes` in **`web/ComfyUI-UML.js`**).

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
