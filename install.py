"""Install dependencies for ComfyUI-UML diagram nodes.

When run directly or from ComfyUI/Manager:
- If comfy_env is available, delegates to comfy_env.install().
- Else, if uv is on PATH and pyproject.toml exists in the plugin root, runs
  `uv sync` to install from pyproject.toml.
- Otherwise runs `pip install -r requirements.txt`.

When run as __main__, exits 0 on success and non-zero on failure.
When called as install(), returns True on success, False on failure (no sys.exit).
"""

import shutil
import subprocess
import sys
from pathlib import Path


def install() -> bool:
    """Run install. Returns True on success, False on failure. Does not sys.exit."""
    _root = Path(__file__).resolve().parent
    req_path = _root / "requirements.txt"
    pyproject_path = _root / "pyproject.toml"

    try:
        from comfy_env import install as comfy_env_install

        print("ComfyUI-UML: Installing via comfy_env…")
        comfy_env_install()
        print("ComfyUI-UML: comfy_env install completed.")
        return True
    except ImportError:
        pass

    if uv_available() and pyproject_path.is_file():
        print("ComfyUI-UML: Installing via uv sync…")
        try:
            subprocess.run(
                [shutil.which("uv"), "sync"],
                cwd=_root,
                check=True,
                capture_output=True,
                text=True,
            )
            print("ComfyUI-UML: uv sync completed.")
            return True
        except subprocess.CalledProcessError as e:
            print(
                "ComfyUI-UML: uv sync failed (exit %d). Falling back to pip." % e.returncode,
                file=sys.stderr,
            )
            if e.stderr:
                sys.stderr.write(e.stderr)

    if not req_path.is_file():
        print("ComfyUI-UML: requirements.txt not found; nothing to install.", file=sys.stderr)
        return False

    print("ComfyUI-UML: Installing via pip -r requirements.txt…")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("ComfyUI-UML: pip install completed.")
        return True
    except subprocess.CalledProcessError as e:
        print(
            "ComfyUI-UML: pip install failed (exit %d): %s"
            % (e.returncode, e.stderr.strip() if e.stderr else "see above"),
            file=sys.stderr,
        )
        return False


def uv_available() -> bool:
    return shutil.which("uv") is not None


if __name__ == "__main__":
    sys.exit(0 if install() else 1)
