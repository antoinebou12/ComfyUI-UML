"""
Execute Kroki plan steps 1-5: resolve type -> source -> encode -> call -> consume.
Run from repo root: py -3 scripts/execute_kroki_plan.py
"""
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from kroki_client import (
    get_kroki_url,
    render_web,
    DIAGRAM_TYPES,
    SUPPORTED_FORMATS,
)
from nodes.default_code import get_default_code

def main():
    # Step 1: Resolve diagram type
    diagram_type = "mermaid"
    output_format = "svg"
    if diagram_type not in DIAGRAM_TYPES:
        print(f"Unsupported type: {diagram_type}")
        return 1
    if output_format not in SUPPORTED_FORMATS.get(diagram_type, []):
        print(f"Format {output_format} not supported for {diagram_type}")
        return 1

    # Step 2: Get diagram source
    diagram_source = get_default_code(diagram_type)
    if not (diagram_source or "").strip():
        print("Empty diagram source")
        return 1

    base_url = "https://kroki.io"
    timeout = 30.0

    # Step 3 & 4: Encode and call Kroki (POST)
    print("Calling Kroki...")
    data = render_web(
        kroki_url=base_url,
        diagram_type=diagram_type,
        diagram_source=diagram_source,
        output_format=output_format,
        timeout=timeout,
    )

    # Step 5: Consume result
    out_dir = root / "web" / "uml"
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "svg" if output_format == "svg" else output_format
    filename = f"uml_{diagram_type}_{int(time.time() * 1000)}.{ext}"
    filepath = out_dir / filename
    filepath.write_bytes(data)
    print("Wrote", filepath)

    kroki_url_out = get_kroki_url(
        kroki_url=base_url,
        diagram_type=diagram_type,
        diagram_source=diagram_source,
        output_format=output_format,
    )
    print("kroki_url:", kroki_url_out[:80] + "...")
    print("Viewer: viewer.html?url=" + kroki_url_out[:60] + "...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
