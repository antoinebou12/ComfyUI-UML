# Agent notes (ComfyUI-UML)

Short guidance for AI assistants and contributors working in this repository.

## Verify before you finish

CI and **`nodes/comfy-env.toml`** target **Python 3.12** (see [`.github/workflows/pytest.yml`](.github/workflows/pytest.yml)).

From the repository root:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q --tb=short
```

Optional: local Mermaid renderer dependencies (see [web/js/package.json](web/js/package.json)):

```bash
cd web/js && npm ci
```

Pytest sets **`COMFYUI_UML_PYTEST=1`** via root [conftest.py](conftest.py) so the plugin [__init__.py](__init__.py) does not load the full ComfyUI node stack during collection. CI sets the same variable in [.github/workflows/pytest.yml](.github/workflows/pytest.yml), then runs **`npm ci`** in **`web/js`** so local Mermaid dependencies stay installable.

## Risky change checklist (ordered)

Use this for edits that touch rendering, URLs, LLM output, or the viewer:

1. **Reproduce** the scenario (widget vs `code_input`, `web` vs `local`, format vs `diagram_type`).
2. **Read the call chain**: [nodes/kroki_client.py](nodes/kroki_client.py) (`render`, `render_web`, `get_kroki_url`, `kroki_options_from_widgets`) and [nodes/uml_diagram.py](nodes/uml_diagram.py) (`UMLDiagram.run` and helpers).
3. **Implement** the smallest diff that fixes one concern.
4. **Run** `ruff check` and `pytest` again.

For large or cross-cutting work (diagram + LLM + routes + CI), use an explicit step-by-step plan first. If you have the **uml-mcp** repo available, the skill at `uml-mcp/.skill/skills/sequential-thinking/SKILL.md` describes ordered reasoning and revision; apply the same discipline here when scope spans multiple files.

## Context7 (library docs)

When changing **httpx**, **Pillow** / image bytes handling, **torch** tensor layout for `IMAGE` outputs, or the **kroki** Python client, use **Context7** (or another up-to-date docs source) in Cursor to confirm APIs for the versions in [pyproject.toml](pyproject.toml) and the lockfile. Do not rely on stale training cutoffs for those libraries.

Context7 is a **Cursor MCP** capability, not a Python dependency of this project.

## Layout pointers

| Area | Files |
|------|--------|
| Kroki HTTP / options | [nodes/kroki_client.py](nodes/kroki_client.py) |
| UML Render node | [nodes/uml_diagram.py](nodes/uml_diagram.py) |
| HTTP routes / proxy | [nodes/uml_routes.py](nodes/uml_routes.py) |
| Viewer URL | [nodes/uml_viewer_url.py](nodes/uml_viewer_url.py) |
| LLM nodes | [nodes/uml_llm_*.py](nodes/) |
| Headless pytest | [conftest.py](conftest.py), [tests/conftest.py](tests/conftest.py) |

User-facing testing detail: [docs/Testing.md](docs/Testing.md).
