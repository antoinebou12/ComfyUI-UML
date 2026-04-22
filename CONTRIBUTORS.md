# Contributing to ComfyUI-UML

Thanks for helping improve ComfyUI-UML.

## Getting started

1. **Clone** the repository and open it in your editor.
2. **Install dev dependencies** (pick one):
   - `uv sync --extra dev` (recommended if you use [uv](https://docs.astral.sh/uv/))
   - `pip install -e ".[dev]"`
3. **Run tests:** `uv run pytest` or `pytest` (from the repo root).
4. **Lint/format:** `uv run ruff check .` and `uv run ruff format .`, or install [pre-commit](https://pre-commit.com/) and run `pre-commit install`.

See [docs/Testing.md](docs/Testing.md) for CI (pytest, comfy-test) and mock LLM behavior.

## Pull requests

- Keep changes focused on one concern when possible.
- Add or update tests when you change behavior users rely on.
- Ensure `pytest` and `ruff check` pass locally before opening a PR.

Use the pull request template checklist when you open a PR.

## Dependency updates

- **Dependabot** opens PRs for Python (`pyproject.toml` / lockfile where applicable), npm under `web/js`, and GitHub Actions.
- **Renovate** is enabled with a [dependency dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) and focuses on updates that do not overlap Dependabot (for example, grouped Action bumps). If two bots open the same update, close one and keep the preferred PR.

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities.

## Code of conduct

Be respectful and constructive in issues and pull requests. Harassment and abuse are not tolerated.
