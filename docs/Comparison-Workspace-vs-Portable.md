# ComfyUI-UML: Workspace vs Portable Comparison

**Compared:** OneDrive workspace vs ComfyUI portable install  
**Date:** 2026-02-24  
**Paths:**
- **Workspace:** `c:\Users\antoi\OneDrive\Bureau\ComfyUI-UML`
- **Portable:** `E:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-UML`

---

## Files only in workspace (missing on portable)

| File | Note |
|------|------|
| `nodes/comfy-env.toml` | Comfy-env config for isolated node env (python 3.10, httpx, kroki). Portable has no comfy-env.toml under nodes. |
| `.ruff_cache/*` | Lint cache (optional, can ignore). |
| `.venv/*` | Local venv (optional, can ignore). |

---

## Files that differ

### `__init__.py`

| Aspect | Workspace | Portable |
|--------|-----------|----------|
| **Node loading** | Uses `importlib` to load nodes as `comfyui_uml_nodes` (avoids clash with ComfyUI’s `nodes`). | Uses relative imports: `from .nodes import ...`, `from .nodes.uml_routes import ...`. |
| **COMFYUI_UML_SKIP_COMFY_ENV** | Checked; when set, skips both comfy_env and local install. | Not checked; no skip-env or local install fallback. |
| **Local install fallback** | On `ImportError` for comfy_env, runs local `install.install()` (with same skip-env check). | On `ImportError` does nothing (`pass`). |
| **Debug print** | None. | Prints `ComfyUI-UML: NODE_CLASS_MAPPINGS loaded (4 nodes): ...` after loading nodes. |

**Summary:** Workspace has the importlib fix (no node name clash), skip-env support, and local install fallback. Portable has the older relative-import + debug-print patch from another agent.

### `install.py`

| Aspect | Workspace | Portable |
|--------|-----------|----------|
| **Return type** | `install() -> bool`; returns `True`/`False`, no `sys.exit()` inside. | `install() -> None`; returns nothing. |
| **On pip failure** | Returns `False`. | Calls `sys.exit(1)` (can kill ComfyUI if called from `__init__.py`). |
| **When run as script** | `sys.exit(0 if install() else 1)`. | `install()` only (exit code always 0). |

**Summary:** Workspace is the “installer broken” fix: safe when called at load time; portable is the old version that can crash ComfyUI on install failure.

### `comfy-env-root.toml`

| Workspace | Portable |
|-----------|----------|
| Has a third comment line: “If Manager reports ‘Env: not installed’, run: python install.py … See docs/Testing.md.” | Only the first two comment lines. |

### `docs/Testing.md`

| Workspace | Portable |
|-----------|----------|
| Includes sections: **"Env: not installed"**, **"Install these nodes" / "Installer broken"**, **"Node 'UMLDiagram' not found"**, plus comfy_env CLI command for portable Windows. | Stops after “Known issue: graphToPrompt validation failures”; none of the troubleshooting sections above. |

### `prestartup_script.py`

Same in both (comfy_env `setup_env()` with ImportError/exception handling).

---

## Files only in portable

- `__pycache__/*` and `nodes/__pycache__/*` (runtime cache; ignore).
- `web/js/mappings.json` (generated; may exist in workspace under web/js).
- `web/uml/*.svg` (generated outputs; optional).

No source files are only in portable.

---

## Recommendation

1. **Overwrite portable from workspace** so the running ComfyUI copy matches the repo:
   - Copy (or robocopy / xcopy) from `c:\Users\antoi\OneDrive\Bureau\ComfyUI-UML` to `E:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-UML`, excluding `.git`, `.venv`, `.ruff_cache`, `__pycache__`.
   - Or, if the portable folder is a Git clone: run `git pull` there and restart ComfyUI.

2. **Restart ComfyUI** after syncing so it loads:
   - The importlib-based `__init__.py` (no node name clash),
   - The safe `install.py` (no `sys.exit` at load time),
   - And the new docs/comfy-env comment.

3. **Optional:** Copy `nodes/comfy-env.toml` from workspace to portable if you want comfy-env to use that config for the nodes subfolder (e.g. for isolation).

4. **Do not re-apply the portable-only patches:** The debug print in `__init__.py` and the relative-import version are superseded by the workspace’s importlib + skip-env + local install fallback; keeping the workspace version is recommended.

---

## One-line summary per differing file

| File | Summary |
|------|---------|
| `__init__.py` | Workspace: importlib load as `comfyui_uml_nodes` + skip-env + local install fallback. Portable: relative import + debug print, no skip-env/fallback. |
| `install.py` | Workspace: `install()` returns bool, no sys.exit in body. Portable: old version with sys.exit(1) on pip failure. |
| `comfy-env-root.toml` | Workspace: extra comment with install steps. Portable: no extra comment. |
| `docs/Testing.md` | Workspace: Env not installed, Installer broken, Node not found sections + CLI. Portable: ends at graphToPrompt section. |
| `nodes/comfy-env.toml` | Workspace only; portable does not have this file. |
