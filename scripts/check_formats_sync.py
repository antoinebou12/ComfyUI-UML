#!/usr/bin/env python3
"""
Check that web/ComfyUI-UML.js SUPPORTED_FORMATS stays in sync with nodes/kroki_client.py.
Run from repo root: python scripts/check_formats_sync.py
Exits 0 if in sync, 1 if they differ (and prints diff).
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_PATH = REPO_ROOT / "web" / "ComfyUI-UML.js"


def get_py_formats():
    sys.path.insert(0, str(REPO_ROOT))
    from nodes.kroki_client import SUPPORTED_FORMATS
    return {k: list(v) for k, v in SUPPORTED_FORMATS.items()}


def get_js_formats():
    text = JS_PATH.read_text(encoding="utf-8")
    # Extract the object between "const SUPPORTED_FORMATS = {" and "};"
    start = text.find("const SUPPORTED_FORMATS = {")
    if start == -1:
        raise SystemExit("check_formats_sync: could not find SUPPORTED_FORMATS in JS")
    start = text.index("{", start) + 1
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    block = text[start : i - 1]
    out = {}
    # Match lines like:   actdiag: ["png", "svg", "pdf"],
    for m in re.finditer(r"\s*(\w+):\s*\[(.*?)\]\s*,?", block, re.DOTALL):
        key = m.group(1)
        arr = m.group(2)
        values = [s.strip().strip('"') for s in arr.split(",") if s.strip()]
        out[key] = values
    return out


def main():
    if not JS_PATH.exists():
        print(f"JS file not found: {JS_PATH}", file=sys.stderr)
        return 1
    try:
        py_f = get_py_formats()
        js_f = get_js_formats()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if py_f == js_f:
        return 0
    only_py = set(py_f) - set(js_f)
    only_js = set(js_f) - set(py_f)
    diff_keys = [k for k in py_f if k in js_f and py_f[k] != js_f[k]]
    if only_py:
        print("Only in nodes/kroki_client.py:", sorted(only_py))
    if only_js:
        print("Only in web/ComfyUI-UML.js:", sorted(only_js))
    for k in diff_keys:
        print(f"Mismatch {k}: Python {py_f[k]} vs JS {js_f[k]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
