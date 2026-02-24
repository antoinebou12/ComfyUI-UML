"""Generate workflows/uml_all_diagrams.json with 28 nodes and groups."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from kroki_client import DIAGRAM_TYPES, SUPPORTED_FORMATS
from nodes.default_code import get_default_code

FORMAT_ORDER = ["png", "svg", "jpeg", "pdf", "txt", "base64"]


def format_index(diagram_type: str) -> int:
    allowed = SUPPORTED_FORMATS.get(diagram_type, ["png"])
    for i, fmt in enumerate(FORMAT_ORDER):
        if fmt in allowed:
            return i
    return 0


def build_single_node_workflow(diagram_type: str, type_index: int) -> dict:
    """Build a workflow with one UMLDiagram node for the given diagram type."""
    code = get_default_code(diagram_type)
    fmt_idx = format_index(diagram_type)
    outputs = [
        {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
        {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
        {"name": "kroki_url", "type": "STRING", "links": None, "slot_index": 2, "shape": 3},
    ]
    node = {
        "id": 1,
        "type": "UMLDiagram",
        "pos": [100, 100],
        "size": [400, 300],
        "flags": {},
        "order": 0,
        "mode": 0,
        "outputs": outputs,
        "properties": {"Node name for S/R": "UMLDiagram"},
        "widgets_values": [0, "https://kroki.io", type_index, code, fmt_idx],
    }
    return {
        "lastNodeId": 1,
        "lastLinkId": 0,
        "nodes": [node],
        "links": [],
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }


def main() -> None:
    workflows_dir = root / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    outputs = [
        {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
        {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
        {"name": "kroki_url", "type": "STRING", "links": None, "slot_index": 2, "shape": 3},
    ]
    nodes = []
    for i, dtype in enumerate(DIAGRAM_TYPES):
        code = get_default_code(dtype)
        fmt_idx = format_index(dtype)
        col, row = i % 4, i // 4
        x, y = 100 + col * 420, 100 + row * 320
        nodes.append({
            "id": i + 1,
            "type": "UMLDiagram",
            "pos": [x, y],
            "size": [400, 300],
            "flags": {},
            "order": i,
            "mode": 0,
            "outputs": list(outputs),
            "properties": {"Node name for S/R": "UMLDiagram"},
            "widgets_values": [0, "https://kroki.io", i, code, fmt_idx],
        })

        # Write one workflow per diagram type
        per_type = build_single_node_workflow(dtype, i)
        out_per = workflows_dir / f"uml_{dtype}.json"
        with open(out_per, "w", encoding="utf-8") as f:
            json.dump(per_type, f, indent=2)
        print("Wrote", out_per)

    groups = [
        {
            "title": "UML (PlantUML, Mermaid, GraphViz, D2, ERD, Nomnoml, UMLet)",
            "bound": [100, 100, 1780, 640],
            "nodes": [17, 12, 11, 6, 9, 13, 24],
        },
        {
            "title": "Block / Sequence diagrams",
            "bound": [100, 420, 1780, 640],
            "nodes": [1, 2, 19, 14, 15, 18],
        },
        {
            "title": "Data (DBML, Vega, Vega-Lite, WaveDrom)",
            "bound": [100, 740, 1780, 420],
            "nodes": [7, 25, 26, 27],
        },
        {
            "title": "Other (BPMN, Bytefield, C4, Ditaa, Excalidraw, Pikchr, Structurizr, Svgbob, Symbolator, TikZ, WireViz)",
            "bound": [100, 1160, 1780, 740],
            "nodes": [3, 4, 5, 8, 10, 16, 20, 21, 22, 23, 28],
        },
    ]
    wf = {
        "lastNodeId": 28,
        "lastLinkId": 0,
        "nodes": nodes,
        "links": [],
        "groups": groups,
        "config": {},
        "extra": {},
        "version": 0.4,
    }
    out_all = workflows_dir / "uml_all_diagrams.json"
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)
    print("Wrote", out_all)


if __name__ == "__main__":
    main()
