"""Pytest root hooks: headless plugin init and ignore plugin __init__ as a test module."""

import os
from pathlib import Path

os.environ["COMFYUI_UML_PYTEST"] = "1"

_ROOT = Path(__file__).resolve().parent


def pytest_ignore_collect(collection_path, config):
    try:
        p = Path(collection_path).resolve()
    except (TypeError, ValueError):
        return None
    if p == (_ROOT / "__init__.py").resolve():
        return True
    return None
