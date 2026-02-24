"""
Workflow tools: generate diagram workflows and normalize ComfyUI workflow JSON.

Default and "generate": generate workflows, then always normalize workflows/*.json
and example_workflows/*.json in place.

  python scripts/generate_all_diagrams_workflow.py
  python scripts/generate_all_diagrams_workflow.py generate
  → Writes workflows/uml_<type>.json and uml_all_diagrams.json, then normalizes them
    and any example_workflows/*.json

Normalize only (specific files):
  python scripts/generate_all_diagrams_workflow.py normalize workflow.json -o fixed.json
  python scripts/generate_all_diagrams_workflow.py normalize workflows/*.json -o out_dir
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "scripts"))

# -----------------------------------------------------------------------------
# Normalize workflow
# -----------------------------------------------------------------------------


def _is_links_corrupted(links: list) -> bool:
    """True if links should be rebuilt (empty, array-style, or all-null entries)."""
    if not isinstance(links, list):
        return True
    if len(links) == 0:
        return False
    first = links[0]
    if isinstance(first, list):
        return True
    if isinstance(first, dict):
        required = {"id", "origin_id", "origin_slot", "target_id", "target_slot", "type"}
        for L in links:
            if not isinstance(L, dict) or required - set(L.keys()):
                return True
            if L.get("origin_id") is None and L.get("target_id") is None:
                return True
        return False
    return True


def _rebuild_links(nodes: list) -> list[dict]:
    """Build links array from node inputs/outputs. Returns list of link objects."""
    id_to_origin: dict[int, tuple[int, int, str]] = {}
    id_to_target: dict[int, tuple[int, int]] = {}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if nid is None:
            continue
        for out in node.get("outputs") or []:
            if not isinstance(out, dict):
                continue
            links_out = out.get("links")
            slot = out.get("slot_index", 0)
            typ = out.get("type", "STRING")
            if isinstance(links_out, list):
                for link_id in links_out:
                    if link_id is not None:
                        id_to_origin[link_id] = (nid, slot, typ)
            elif links_out is not None:
                id_to_origin[links_out] = (nid, slot, typ)
        for inp in node.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            link_id = inp.get("link")
            slot = inp.get("slot_index", 0)
            if link_id is not None:
                id_to_target[link_id] = (nid, slot)

    links = []
    for link_id in sorted(set(id_to_origin.keys()) | set(id_to_target.keys())):
        orig = id_to_origin.get(link_id)
        tgt = id_to_target.get(link_id)
        if orig is None or tgt is None:
            continue
        links.append({
            "id": link_id,
            "origin_id": orig[0],
            "origin_slot": orig[1],
            "target_id": tgt[0],
            "target_slot": tgt[1],
            "type": orig[2],
        })
    return links


def _node_rect(node: dict) -> tuple[float, float, float, float] | None:
    """(x, y, w, h) from node pos/size, or None."""
    pos = node.get("pos")
    size = node.get("size")
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return None
    if not isinstance(size, (list, tuple)) or len(size) < 2:
        return None
    return (float(pos[0]), float(pos[1]), float(size[0]), float(size[1]))


def _ensure_group_bounds(groups: list, nodes: list) -> None:
    """In-place: set bound on each group if missing or invalid."""
    node_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id") is not None}
    for g in groups:
        if not isinstance(g, dict):
            continue
        bound = g.get("bound")
        if isinstance(bound, (list, tuple)) and len(bound) >= 4:
            try:
                [float(bound[0]), float(bound[1]), float(bound[2]), float(bound[3])]
                continue
            except (TypeError, ValueError):
                pass
        node_ids = g.get("nodes")
        if not isinstance(node_ids, list):
            g["bound"] = [0, 0, 400, 300]
            continue
        rects = []
        for nid in node_ids:
            n = node_by_id.get(nid)
            if n is None:
                continue
            r = _node_rect(n)
            if r is None:
                continue
            rects.append(r)
        if not rects:
            g["bound"] = [0, 0, 400, 300]
            continue
        min_x = min(r[0] for r in rects)
        min_y = min(r[1] for r in rects)
        max_x = max(r[0] + r[2] for r in rects)
        max_y = max(r[1] + r[3] for r in rects)
        padding = 20
        g["bound"] = [
            max(0, min_x - padding),
            max(0, min_y - padding),
            max_x - min_x + 2 * padding,
            max_y - min_y + 2 * padding,
        ]


def normalize(data: dict) -> dict:
    """Return a normalized copy of the workflow (links, groups, root keys)."""
    data = json.loads(json.dumps(data))
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
        data["nodes"] = nodes
    links = data.get("links")
    if not isinstance(links, list) or _is_links_corrupted(links):
        links = _rebuild_links(nodes)
        data["links"] = links
    last_link = data.get("lastLinkId") if data.get("lastLinkId") is not None else data.get("last_link_id")
    if links and (last_link is None or last_link == 0):
        last_link = max(L.get("id", 0) for L in links if isinstance(L, dict))
    if last_link is not None:
        data["lastLinkId"] = int(last_link)
    data.pop("last_link_id", None)
    last_node = data.get("lastNodeId") or data.get("last_node_id")
    if last_node is None and nodes:
        last_node = max(n.get("id", 0) for n in nodes if isinstance(n, dict))
    if last_node is not None:
        data["lastNodeId"] = int(last_node)
    data.pop("last_node_id", None)
    groups = data.get("groups")
    if isinstance(groups, list):
        _ensure_group_bounds(groups, nodes)
    if "config" not in data:
        data["config"] = {}
    if "extra" not in data:
        data["extra"] = {}
    if "version" not in data:
        data["version"] = 0.4
    return data


def _expand_globs(path_list: list) -> list:
    out: list = []
    for p in path_list:
        if p == "-":
            out.append("-")
            continue
        path = Path(p)
        if "*" in path.name or "?" in path.name:
            out.extend(sorted(path.parent.glob(path.name)))
        else:
            out.append(path.resolve())
    return out


def run_normalize(args: argparse.Namespace) -> int:
    inputs = args.input if isinstance(args.input, list) else [args.input]
    if not inputs or (len(inputs) == 1 and inputs[0] == "-"):
        inputs = ["-"] if not inputs or inputs[0] == "-" else inputs
    inputs = _expand_globs(inputs)
    parser = args._parser
    if len(inputs) > 1 and "-" in inputs:
        parser.error("stdin '-' not allowed with multiple inputs")
    if len(inputs) == 1 and inputs[0] == "-":
        raw = json.load(sys.stdin)
        out = normalize(raw)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
        else:
            json.dump(out, sys.stdout, indent=args.indent or None, ensure_ascii=False)
        return 0
    out_path = Path(args.output) if args.output else None
    if len(inputs) > 1 and out_path is not None and not out_path.is_dir():
        parser.error("with multiple inputs, -o must be a directory or omitted (in-place)")
    if len(inputs) > 1 and out_path is not None:
        out_path.mkdir(parents=True, exist_ok=True)
    for inp in inputs:
        if inp == "-":
            continue
        path = inp if isinstance(inp, Path) else Path(inp)
        if not path.is_file():
            parser.error(f"not a file: {path}")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        out = normalize(raw)
        if out_path is not None:
            dest = out_path / path.name if out_path.is_dir() else out_path
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            print("Wrote", dest)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            print("Normalized", path)
    return 0


# -----------------------------------------------------------------------------
# Generate workflows
# -----------------------------------------------------------------------------

FORMAT_ORDER = ["png", "svg", "jpeg", "pdf", "txt", "base64"]


def _load_kroki_and_default_code() -> None:
    global DIAGRAM_TYPES, SUPPORTED_FORMATS, get_default_code
    from nodes.kroki_client import DIAGRAM_TYPES as _DT, SUPPORTED_FORMATS as _SF  # noqa: E402
    DIAGRAM_TYPES = _DT
    SUPPORTED_FORMATS = _SF
    import nodes.default_code as _default_code
    get_default_code = _default_code.get_default_code


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


def run_generate() -> int:
    _load_kroki_and_default_code()
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
        per_type = normalize(build_single_node_workflow(dtype, i))
        out_per = workflows_dir / f"uml_{dtype}.json"
        with open(out_per, "w", encoding="utf-8") as f:
            json.dump(per_type, f, indent=2)
        print("Wrote", out_per)
    groups = [
        {"title": "UML (PlantUML, Mermaid, GraphViz, D2, ERD, Nomnoml, UMLet)", "nodes": [17, 12, 11, 6, 9, 13, 24]},
        {"title": "Block / Sequence diagrams", "nodes": [1, 2, 19, 14, 15, 18]},
        {"title": "Data (DBML, Vega, Vega-Lite, WaveDrom)", "nodes": [7, 25, 26, 27]},
        {"title": "Other (BPMN, Bytefield, C4, Ditaa, Excalidraw, Pikchr, Structurizr, Svgbob, Symbolator, TikZ, WireViz)", "nodes": [3, 4, 5, 8, 10, 16, 20, 21, 22, 23, 28]},
    ]
    wf = normalize({
        "lastNodeId": 28,
        "lastLinkId": 0,
        "nodes": nodes,
        "links": [],
        "groups": groups,
        "config": {},
        "extra": {},
        "version": 0.4,
    })
    out_all = workflows_dir / "uml_all_diagrams.json"
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)
    print("Wrote", out_all)
    return 0


def run_generate_and_normalize() -> int:
    """Generate workflows then normalize workflows/*.json and example_workflows/*.json in place."""
    run_generate()
    workflows_dir = root / "workflows"
    example_dir = root / "example_workflows"
    to_normalize: list[Path] = []
    if workflows_dir.is_dir():
        to_normalize.extend(sorted(workflows_dir.glob("*.json")))
    if example_dir.is_dir():
        to_normalize.extend(sorted(example_dir.glob("*.json")))
    if not to_normalize:
        return 0
    # Build a minimal namespace for run_normalize (in-place, no -o)
    class Args:
        input = [str(p) for p in to_normalize]
        output = None
        indent = 2
        _parser = None

    args = Args()
    _parser = argparse.ArgumentParser()
    _parser.error = lambda msg: sys.exit(2)
    args._parser = _parser
    return run_normalize(args)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate workflow JSON and optionally normalize.")
    subparsers = parser.add_subparsers(dest="command", help="command")
    subparsers.add_parser("generate", help="Generate workflows then normalize workflows/* and example_workflows/*")
    norm_parser = subparsers.add_parser("normalize", help="Only normalize given workflow JSON")
    norm_parser.set_defaults(_parser=norm_parser)
    norm_parser.add_argument("input", nargs="*", default=["-"], help="Input JSON file(s); '-' for stdin")
    norm_parser.add_argument("-o", "--output", default=None, help="Output file or directory")
    norm_parser.add_argument("--indent", type=int, default=2, help="JSON indent (default 2); 0 for compact")
    args = parser.parse_args()
    if args.command == "normalize":
        return run_normalize(args)
    if args.command == "generate":
        return run_generate_and_normalize()
    # Default: same as generate (generate then normalize)
    return run_generate_and_normalize()


if __name__ == "__main__":
    sys.exit(main())
