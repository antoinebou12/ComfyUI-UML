"""Format workflow JSON with indent=2, ensure_ascii=True, and trailing newline."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
dirs = [root / "workflows", root / "example_workflows"]
paths = sys.argv[1:] if len(sys.argv) > 1 else [p for d in dirs if d.is_dir() for p in sorted(d.glob("*.json"))]

for path in paths:
    path = Path(path)
    if not path.is_file():
        continue
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
            f.write("\n")
        print("Formatted", path)
    except Exception as e:
        print(path, e, file=sys.stderr)
