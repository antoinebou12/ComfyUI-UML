"""
Single pipeline for workflow generation, normalization, viewer injection, and format sync.

Default (no subcommand): full pipeline — generate workflows, normalize, add viewer to
non-CPU workflows, normalize again, then check that web/ComfyUI-UML.js SUPPORTED_FORMATS
matches nodes/kroki_client.py. All workflow JSON is written with indent=2 and trailing
newline. Exits 1 if formats are out of sync. The generate step also produces
uml_viewer_formats_test.json for testing the diagram viewer with multiple output formats
(URL, PNG, SVG, PDF, TXT).

  python scripts/generate_all_diagrams_workflow.py

Subcommands:
  generate   — Generate workflows and normalize workflows/*.json (no add-viewer, no sync check).
  sync-formats — Update web/ComfyUI-UML.js SUPPORTED_FORMATS from nodes/kroki_client.py only.
  normalize  — Only normalize given workflow JSON. Omit input to normalize workflows/ in place.
               Examples: normalize workflow.json -o fixed.json; normalize - (stdin → stdout).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "scripts"))

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Normalize workflow
# -----------------------------------------------------------------------------


def _is_links_corrupted(links: list) -> bool:
    if not isinstance(links, list):
        return True
    if len(links) == 0:
        return False
    first = links[0]
    if isinstance(first, list):
        return True
    if first is not None and isinstance(first, dict):
        required = {"id", "origin_id", "origin_slot", "target_id", "target_slot", "type"}
        for link in links:
            if not link or not isinstance(link, dict):
                return True
            if not required.issubset(link.keys()):
                return True
            if link.get("origin_id") is None and link.get("target_id") is None:
                return True
        return False
    return True


def _node_rect(node: dict) -> list[float] | None:
    pos = node.get("pos")
    size = node.get("size")
    if not isinstance(pos, list) or len(pos) < 2 or not isinstance(size, list) or len(size) < 2:
        return None
    try:
        x, y = float(pos[0]), float(pos[1])
        w, h = float(size[0]), float(size[1])
        if all(math.isfinite(v) for v in (x, y, w, h)):
            return [x, y, w, h]
    except (TypeError, ValueError):
        pass
    return None


def _rebuild_links(nodes: list) -> list[dict]:
    id_to_origin: dict[int | str, tuple[int | str, int, str]] = {}
    id_to_target: dict[int | str, tuple[int | str, int]] = {}

    for node in nodes or []:
        if not node or not isinstance(node, dict):
            continue
        nid = node.get("id")
        if nid is None:
            continue

        for i, out in enumerate(node.get("outputs") or []):
            if not out or not isinstance(out, dict):
                continue
            slot = out.get("slot_index") if out.get("slot_index") is not None else i
            typ = out.get("type") or "STRING"
            links_out = out.get("links")
            if isinstance(links_out, list):
                for link_id in links_out:
                    if link_id is not None:
                        id_to_origin[link_id] = (nid, slot, typ)
            elif links_out is not None:
                id_to_origin[links_out] = (nid, slot, typ)

        for i, inp in enumerate(node.get("inputs") or []):
            if not inp or not isinstance(inp, dict):
                continue
            link_id = inp.get("link")
            if link_id is not None:
                slot = inp.get("slot_index") if inp.get("slot_index") is not None else i
                id_to_target[link_id] = (nid, slot)

    link_ids = sorted(
        set(id_to_origin.keys()) | set(id_to_target.keys()), key=lambda x: (type(x).__name__, x)
    )
    links = []
    for link_id in link_ids:
        orig = id_to_origin.get(link_id)
        tgt = id_to_target.get(link_id)
        if not orig or not tgt:
            continue
        links.append(
            {
                "id": link_id,
                "origin_id": orig[0],
                "origin_slot": orig[1],
                "target_id": tgt[0],
                "target_slot": tgt[1],
                "type": orig[2],
            }
        )
    return links


def _ensure_group_bounds(groups: list, nodes: list) -> None:
    node_by_id = {}
    for n in nodes or []:
        if n and isinstance(n, dict) and n.get("id") is not None:
            node_by_id[n["id"]] = n

    for group in groups or []:
        if not group or not isinstance(group, dict):
            continue
        bound = group.get("bound")
        if isinstance(bound, list) and len(bound) >= 4:
            try:
                nums = [float(bound[0]), float(bound[1]), float(bound[2]), float(bound[3])]
                if all(math.isfinite(n) for n in nums):
                    continue
            except (TypeError, ValueError):
                pass
        node_ids = group.get("nodes") if isinstance(group.get("nodes"), list) else []
        rects = []
        for nid in node_ids:
            node = node_by_id.get(nid)
            if not node:
                continue
            r = _node_rect(node)
            if r:
                rects.append(r)
        if not rects:
            group["bound"] = [0, 0, 400, 300]
            continue
        padding = 20
        min_x = min(r[0] for r in rects) - padding
        min_y = min(r[1] for r in rects) - padding
        max_x = max(r[0] + r[2] for r in rects) + padding
        max_y = max(r[1] + r[3] for r in rects) + padding
        group["bound"] = [
            max(0, min_x),
            max(0, min_y),
            max_x - min_x,
            max_y - min_y,
        ]


def _sanitize_groups(groups: list) -> list:
    if not isinstance(groups, list):
        return []
    out = []
    default_bound = [0, 0, 400, 300]
    for g in groups:
        if g is None or not isinstance(g, dict):
            continue
        b = g.get("bound")
        valid = False
        if isinstance(b, list) and len(b) >= 4:
            try:
                valid = all(math.isfinite(float(v)) for v in b[:4])
            except (TypeError, ValueError):
                pass
        if not valid:
            g["bound"] = default_bound.copy()
        out.append(g)
    return out


def _node_ensure_class_type_after_type(node: dict) -> None:
    """Ensure node has class_type (from type if missing) and place it right after 'type'
    for API/graphToPrompt compatibility (some readers expect class_type early in the object).
    Mutates node in place by reordering keys.
    """
    if not node or not isinstance(node, dict) or "type" not in node:
        return
    ct = node.get("class_type") or node["type"]
    # Rebuild dict with class_type immediately after type so serialized JSON has correct order
    new_node: dict = {}
    for k, v in node.items():
        if k == "class_type":
            continue
        new_node[k] = v
        if k == "type":
            new_node["class_type"] = ct
    node.clear()
    node.update(new_node)


def _node_ensure_inputs(node: dict) -> None:
    """Ensure node has an 'inputs' array (empty if missing) for graphToPrompt compatibility.
    ComfyUI frontend graphToPrompt can produce nodes without class_type when graph nodes lack inputs.
    """
    if not node or not isinstance(node, dict):
        return
    if "inputs" not in node or not isinstance(node.get("inputs"), list):
        node["inputs"] = []


def _node_order_keys_for_graph_to_prompt(node: dict) -> None:
    """Reorder node keys so id, type, class_type appear first and inputs last.
    Ensures serialized JSON has class_type before inputs for order-sensitive graphToPrompt readers.
    Mutates node in place.
    """
    if not node or not isinstance(node, dict):
        return
    first_keys = ("id", "type", "class_type")
    last_key = "inputs"
    rest = [k for k in node if k not in first_keys and k != last_key]
    # Stable order: id, type, class_type, then rest (preserve relative order), then inputs
    ordered = [k for k in first_keys if k in node]
    ordered.extend(rest)
    if last_key in node:
        ordered.append(last_key)
    new_node = {k: node[k] for k in ordered}
    node.clear()
    node.update(new_node)


def normalize(data: dict) -> dict:
    """Return a normalized copy of the workflow (links, groups, root keys).
    Ensures every node has class_type (from type if missing) for API/graphToPrompt compatibility,
    with class_type placed immediately after type in the node object.
    """
    if not data or not isinstance(data, dict):
        return data

    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    for node in nodes:
        if node and isinstance(node, dict):
            _node_ensure_class_type_after_type(node)
            _node_ensure_inputs(node)
            _node_order_keys_for_graph_to_prompt(node)
    data = dict(data)
    data["nodes"] = nodes

    links = data.get("links")
    if _is_links_corrupted(links):
        data["links"] = _rebuild_links(nodes)
    else:
        data["links"] = links

    last_link = (
        data.get("lastLinkId") if data.get("lastLinkId") is not None else data.get("last_link_id")
    )
    if data.get("links") and (last_link is None or last_link == 0):
        try:
            last_link = max(int(link.get("id") or 0) for link in data["links"])
        except (ValueError, TypeError):
            pass
    if last_link is not None:
        data["lastLinkId"] = int(last_link) if isinstance(last_link, (int, float)) else last_link
    data.pop("last_link_id", None)

    last_node = (
        data.get("lastNodeId") if data.get("lastNodeId") is not None else data.get("last_node_id")
    )
    if last_node is None and nodes:
        try:
            last_node = max(int(n.get("id") or 0) for n in nodes)
        except (ValueError, TypeError):
            pass
    if last_node is not None:
        data["lastNodeId"] = int(last_node) if isinstance(last_node, (int, float)) else last_node
    data.pop("last_node_id", None)

    groups = data.get("groups")
    if not isinstance(groups, list):
        data["groups"] = []
    else:
        _ensure_group_bounds(groups, nodes)
        data["groups"] = _sanitize_groups(groups)

    if data.get("config") is None:
        data["config"] = {}
    if data.get("extra") is None:
        data["extra"] = {}
    if data.get("version") is None:
        data["version"] = 0.4

    return data


def _write_workflow_json(path: Path, data: dict, indent: int = 2) -> None:
    """Write workflow JSON with indent, ensure_ascii=False, and trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent if indent else None, ensure_ascii=False)
        f.write("\n")


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
    parser = args._parser

    # No input → normalize workflows/ in place
    if not inputs:
        workflows_dir = root / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        to_normalize: list[Path] = []
        if workflows_dir.is_dir():
            to_normalize.extend(sorted(workflows_dir.glob("*.json")))
        if not to_normalize:
            logger.info("No JSON files in workflows/.")
            return 0
        logger.info(
            "Normalizing workflows/ in place (%d file(s)).",
            len(to_normalize),
        )
        inputs = [str(p) for p in to_normalize]
    elif len(inputs) == 1 and inputs[0] == "-":
        inputs = ["-"]

    inputs = _expand_globs(inputs)
    if len(inputs) > 1 and "-" in inputs:
        parser.error("stdin '-' not allowed with multiple inputs")
    if len(inputs) == 1 and inputs[0] == "-":
        raw = json.load(sys.stdin)
        out = normalize(raw)
        if args.output:
            _write_workflow_json(Path(args.output), out, indent=args.indent or 2)
            logger.info("Wrote %s", args.output)
        else:
            json.dump(out, sys.stdout, indent=args.indent or None, ensure_ascii=False)
            sys.stdout.write("\n")
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
            _write_workflow_json(Path(dest), out, indent=args.indent or 2)
            logger.info("Wrote %s", dest)
        else:
            _write_workflow_json(Path(path), out, indent=args.indent or 2)
            logger.info("Normalized %s", path)
    return 0


# -----------------------------------------------------------------------------
# Add viewer to workflows (inlined from add_viewer_to_workflows)
# -----------------------------------------------------------------------------


def _has_viewer_node(nodes: list) -> bool:
    return any(n and n.get("type") == "UMLViewerURL" for n in nodes)


def _ensure_uml_outputs(node: dict) -> bool:
    """Ensure UMLDiagram has 4 outputs: IMAGE, path, kroki_url, content_for_viewer. Return True if changed."""
    if not node or node.get("type") != "UMLDiagram":
        return False
    outs = node.get("outputs")
    if not isinstance(outs, list):
        return False
    names = [o.get("name") for o in outs if o and o.get("name")]
    if "content_for_viewer" in names:
        return False
    last_slot = max((o.get("slot_index", i) for i, o in enumerate(outs) if o), default=-1)
    outs.append(
        {
            "name": "content_for_viewer",
            "type": "STRING",
            "links": None,
            "slot_index": last_slot + 1,
            "shape": 3,
        }
    )
    return True


def _first_uml_diagram_id(nodes: list) -> int | None:
    for n in nodes or []:
        if n and n.get("type") == "UMLDiagram":
            return n.get("id")
    return None


def _max_node_id(nodes: list) -> int:
    m = 0
    for n in nodes or []:
        if n and isinstance(n.get("id"), (int, float)):
            m = max(m, int(n["id"]))
    return m


def _max_link_id(links: list) -> int:
    m = 0
    for L in links or []:
        if L and isinstance(L.get("id"), (int, float)):
            m = max(m, int(L["id"]))
    return m


def _add_viewer_to_workflow(data: dict) -> bool:
    """Mutate data: add UMLViewerURL and link from first UMLDiagram. Return True if changed."""
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return False

    any_uml_updated = any(_ensure_uml_outputs(n) for n in nodes)

    if _has_viewer_node(nodes):
        return any_uml_updated

    first_uml_id = _first_uml_diagram_id(nodes)
    if first_uml_id is None:
        return any_uml_updated

    new_node_id = _max_node_id(nodes) + 1
    new_link_id = _max_link_id(data.get("links")) + 1

    for n in nodes:
        if n and n.get("id") == first_uml_id:
            for o in n.get("outputs") or []:
                if o and o.get("name") == "kroki_url":
                    o["links"] = [new_link_id]
                    break
            break

    viewer_pos = [100, 420]
    for n in nodes:
        if n and n.get("id") == first_uml_id:
            pos = n.get("pos")
            size = n.get("size")
            if (
                isinstance(pos, list)
                and len(pos) >= 2
                and isinstance(size, list)
                and len(size) >= 2
            ):
                viewer_pos = [pos[0], pos[1] + size[1] + 20]
            break

    viewer_node = {
        "id": new_node_id,
        "type": "UMLViewerURL",
        "class_type": "UMLViewerURL",
        "pos": viewer_pos,
        "size": [280, 80],
        "flags": {},
        "order": len(nodes),
        "mode": 0,
        "inputs": [{"name": "kroki_url", "type": "STRING", "link": new_link_id}],
        "outputs": [
            {"name": "viewer_url", "type": "STRING", "links": None, "slot_index": 0, "shape": 3}
        ],
        "properties": {"Node name for S/R": "UMLViewerURL"},
        "widgets_values": [],
    }
    nodes.append(viewer_node)

    link = {
        "id": new_link_id,
        "origin_id": first_uml_id,
        "origin_slot": 2,
        "target_id": new_node_id,
        "target_slot": 0,
        "type": "STRING",
    }
    links = data.get("links")
    if not isinstance(links, list):
        links = []
        data["links"] = links
    links.append(link)

    data["lastNodeId"] = new_node_id
    data["lastLinkId"] = new_link_id

    groups = data.get("groups")
    if isinstance(groups, list) and groups:
        g = groups[0]
        if isinstance(g, dict) and "nodes" in g:
            g["nodes"] = list(g["nodes"]) if isinstance(g["nodes"], list) else []
            if new_node_id not in g["nodes"]:
                g["nodes"].append(new_node_id)
            b = g.get("bound")
            if isinstance(b, list) and len(b) >= 4:
                g["bound"] = [b[0], b[1], b[2], b[3] + 120]

    return True


def _run_add_viewer_to_workflows() -> int:
    """Add UMLViewerURL to workflows that have UMLDiagram but not yet UMLViewerURL."""
    workflows_dir = root / "workflows"
    changed = 0
    if not workflows_dir.is_dir():
        return 0
    for path in sorted(workflows_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning("Skip %s: %s", path, e)
            continue
        if _add_viewer_to_workflow(data):
            _write_workflow_json(path, data)
            logger.info("Updated %s", path)
            changed += 1
    return 0


# -----------------------------------------------------------------------------
# Check formats sync (inlined from check_formats_sync)
# -----------------------------------------------------------------------------

JS_PATH = root / "web" / "ComfyUI-UML.js"


def _get_py_supported_formats() -> dict:
    from nodes.kroki_client import SUPPORTED_FORMATS  # noqa: E402

    return {k: list(v) for k, v in SUPPORTED_FORMATS.items()}


def _get_js_supported_formats() -> dict:
    text = JS_PATH.read_text(encoding="utf-8")
    start = text.find("const SUPPORTED_FORMATS = {")
    if start == -1:
        raise SystemExit("Could not find SUPPORTED_FORMATS in web/ComfyUI-UML.js")
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
    for m in re.finditer(r"\s*(\w+):\s*\[(.*?)\]\s*,?", block, re.DOTALL):
        key = m.group(1)
        arr = m.group(2)
        values = [s.strip().strip('"') for s in arr.split(",") if s.strip()]
        out[key] = values
    return out


def _check_formats_sync() -> int:
    """Return 0 if web/ComfyUI-UML.js SUPPORTED_FORMATS matches nodes/kroki_client.py, else 1."""
    if not JS_PATH.exists():
        logger.error("JS file not found: %s", JS_PATH)
        return 1
    try:
        py_f = _get_py_supported_formats()
        js_f = _get_js_supported_formats()
    except Exception as e:
        logger.error("Error: %s", e)
        return 1
    if py_f == js_f:
        return 0
    only_py = set(py_f) - set(js_f)
    only_js = set(js_f) - set(py_f)
    diff_keys = [k for k in py_f if k in js_f and py_f[k] != js_f[k]]
    if only_py:
        logger.info("Only in nodes/kroki_client.py: %s", sorted(only_py))
    if only_js:
        logger.info("Only in web/ComfyUI-UML.js: %s", sorted(only_js))
    for k in diff_keys:
        logger.info("Mismatch %s: Python %s vs JS %s", k, py_f[k], js_f[k])
    return 1


def _sync_js_supported_formats() -> int:
    """Update web/ComfyUI-UML.js SUPPORTED_FORMATS from nodes/kroki_client.py. Return 0 on success."""
    from nodes.kroki_client import SUPPORTED_FORMATS  # noqa: E402

    lines = []
    for key in sorted(SUPPORTED_FORMATS.keys()):
        formats = SUPPORTED_FORMATS[key]
        fmt_str = ", ".join(f'"{f}"' for f in formats)
        lines.append(f"  {key}: [{fmt_str}],")
    inner = "\n" + "\n".join(lines)

    if not JS_PATH.exists():
        logger.error("JS file not found: %s", JS_PATH)
        return 1
    text = JS_PATH.read_text(encoding="utf-8")
    start_marker = "const SUPPORTED_FORMATS = {"
    start = text.find(start_marker)
    if start == -1:
        logger.error("Could not find SUPPORTED_FORMATS in web/ComfyUI-UML.js")
        return 1
    block_start = text.index("{", start) + 1
    depth = 1
    i = block_start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    block_end = i - 1
    new_text = text[:block_start] + inner + text[block_end:]
    JS_PATH.write_text(new_text, encoding="utf-8")
    logger.info("Updated SUPPORTED_FORMATS in %s", JS_PATH)
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


# Placeholder returned when a diagram type has no nodes/defaults/<type>.txt; must match default_code._PLACEHOLDER
_DEFAULT_PLACEHOLDER = "// Enter your diagram source here"


def _validate_default_code_coverage() -> int:
    """Ensure every DIAGRAM_TYPES entry has a default code file. Return 0 if all present, 1 if any missing."""
    missing = [t for t in DIAGRAM_TYPES if get_default_code(t) == _DEFAULT_PLACEHOLDER]
    if not missing:
        return 0
    for t in missing:
        logger.warning("Missing default code for diagram type %s: add nodes/defaults/%s.txt", t, t)
    logger.error("Default code missing for %d diagram type(s); add nodes/defaults/<type>.txt", len(missing))
    return 1


def format_index(diagram_type: str) -> int:
    allowed = SUPPORTED_FORMATS.get(diagram_type, ["png"])
    for i, fmt in enumerate(FORMAT_ORDER):
        if fmt in allowed:
            return i
    return 0


def format_string_to_widget_index(diagram_type: str, format_str: str) -> int:
    """Return the FORMAT_ORDER index for the given format if allowed for diagram_type, else first allowed."""
    allowed = SUPPORTED_FORMATS.get(diagram_type, ["png"])
    fmt = (format_str or "").strip().lower()
    if fmt in allowed:
        for i, f in enumerate(FORMAT_ORDER):
            if f == fmt:
                return i
    return format_index(diagram_type)
def build_single_node_workflow(diagram_type: str, type_index: int) -> dict:
    """Build a workflow with one UMLDiagram node for the given diagram type (no viewer, no links)."""
    code = get_default_code(diagram_type)
    fmt_idx = format_index(diagram_type)
    outputs = [
        {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
        {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
        {"name": "kroki_url", "type": "STRING", "links": None, "slot_index": 2, "shape": 3},
        {"name": "content_for_viewer", "type": "STRING", "links": None, "slot_index": 3, "shape": 3},
    ]
    node = {
        "id": 1,
        "type": "UMLDiagram",
        "class_type": "UMLDiagram",
        "pos": [100, 100],
        "size": [400, 300],
        "flags": {},
        "order": 0,
        "mode": 0,
        "outputs": outputs,
        "properties": {"Node name for S/R": "UMLDiagram"},
        "widgets_values": [0, "https://kroki.io", type_index, code, fmt_idx],
        "inputs": [],
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


def _build_uml_single_node_workflow() -> dict:
    """Build uml_single_node.json: blockdiag SVG, blockdiag PNG, plantuml TXT, each with a viewer.
    Tests viewer with URL, SVG, PNG, and TXT formats."""
    blockdiag_idx = DIAGRAM_TYPES.index("blockdiag")
    plantuml_idx = DIAGRAM_TYPES.index("plantuml")
    blockdiag_code = get_default_code("blockdiag")
    plantuml_code = get_default_code("plantuml")

    outputs_template = [
        {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
        {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
        {"name": "kroki_url", "type": "STRING", "links": None, "slot_index": 2, "shape": 3},
        {"name": "content_for_viewer", "type": "STRING", "links": None, "slot_index": 3, "shape": 3},
    ]

    nodes = []
    links = []
    # Three columns: blockdiag SVG, blockdiag PNG, plantuml TXT
    configs = [
        (blockdiag_idx, blockdiag_code, format_string_to_widget_index("blockdiag", "svg"), 100),
        (blockdiag_idx, blockdiag_code, format_string_to_widget_index("blockdiag", "png"), 540),
        (plantuml_idx, plantuml_code, format_string_to_widget_index("plantuml", "txt"), 980),
    ]
    for i, (dtype_idx, code, fmt_idx, x) in enumerate(configs):
        link_id = i + 1
        diagram_id = i + 1
        viewer_id = i + 4
        outputs = [dict(o) for o in outputs_template]
        outputs[2]["links"] = [link_id]
        nodes.append({
            "id": diagram_id,
            "type": "UMLDiagram",
            "class_type": "UMLDiagram",
            "pos": [x, 100],
            "size": [400, 300],
            "flags": {},
            "order": i,
            "mode": 0,
            "outputs": outputs,
            "properties": {"Node name for S/R": "UMLDiagram"},
            "widgets_values": [0, "https://kroki.io", dtype_idx, code, fmt_idx],
            "inputs": [],
        })
        nodes.append({
            "id": viewer_id,
            "type": "UMLViewerURL",
            "class_type": "UMLViewerURL",
            "pos": [x, 420],
            "size": [280, 80],
            "flags": {},
            "order": 3 + i,
            "mode": 0,
            "outputs": [
                {"name": "viewer_url", "type": "STRING", "links": None, "slot_index": 0, "shape": 3}
            ],
            "properties": {"Node name for S/R": "UMLViewerURL"},
            "widgets_values": [],
            "inputs": [{"name": "kroki_url", "type": "STRING", "link": link_id}],
        })
        links.append({
            "id": link_id,
            "origin_id": diagram_id,
            "origin_slot": 2,
            "target_id": viewer_id,
            "target_slot": 0,
            "type": "STRING",
        })

    return normalize({
        "lastNodeId": 6,
        "lastLinkId": 3,
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    })


def build_single_node_workflow_api(diagram_type: str, type_index: int) -> dict:
    """Build API/prompt format workflow (nodes as object keyed by id) for comfy-test.
    Avoids UI→API conversion that can drop class_type. Single UMLDiagram node, no links.
    """
    code = get_default_code(diagram_type)
    fmt_idx = format_index(diagram_type)
    format_str = FORMAT_ORDER[fmt_idx] if fmt_idx < len(FORMAT_ORDER) else "svg"
    inputs = {
        "backend": "web",
        "kroki_url": "https://kroki.io",
        "diagram_type": diagram_type,
        "code": code,
        "output_format": format_str,
    }
    return {
        "1": {
            "class_type": "UMLDiagram",
            "inputs": inputs,
        }
    }


def _build_viewer_formats_test_workflow() -> dict:
    """Build a workflow that tests the viewer with multiple output formats (URL, PNG, SVG, PDF, TXT).
    Four UMLDiagram nodes (blockdiag png/svg/pdf, plantuml txt) each connected to a UMLViewerURL.
    """
    blockdiag_idx = DIAGRAM_TYPES.index("blockdiag")
    plantuml_idx = DIAGRAM_TYPES.index("plantuml")
    blockdiag_code = get_default_code("blockdiag")
    plantuml_code = get_default_code("plantuml")

    outputs_template = [
        {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
        {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
        {"name": "kroki_url", "type": "STRING", "links": None, "slot_index": 2, "shape": 3},
        {"name": "content_for_viewer", "type": "STRING", "links": None, "slot_index": 3, "shape": 3},
    ]

    nodes = []
    links = []
    base_y = 100
    row_height = 420

    # Blockdiag: png, svg, pdf (diagram ids 1–3, viewer ids 5–7, link ids 1–3)
    for i, fmt in enumerate(["png", "svg", "pdf"]):
        link_id = i + 1
        diagram_id = i + 1
        viewer_id = i + 5
        outputs = [dict(o) for o in outputs_template]
        outputs[2]["links"] = [link_id]
        nodes.append({
            "id": diagram_id,
            "type": "UMLDiagram",
            "class_type": "UMLDiagram",
            "pos": [100, base_y + i * row_height],
            "size": [400, 300],
            "flags": {},
            "order": i,
            "mode": 0,
            "outputs": outputs,
            "properties": {"Node name for S/R": "UMLDiagram"},
            "widgets_values": [
                0,
                "https://kroki.io",
                blockdiag_idx,
                blockdiag_code,
                format_string_to_widget_index("blockdiag", fmt),
            ],
            "inputs": [],
        })
        nodes.append({
            "id": viewer_id,
            "type": "UMLViewerURL",
            "class_type": "UMLViewerURL",
            "pos": [100, base_y + i * row_height + 320],
            "size": [280, 80],
            "flags": {},
            "order": 3 + i,
            "mode": 0,
            "outputs": [
                {"name": "viewer_url", "type": "STRING", "links": None, "slot_index": 0, "shape": 3}
            ],
            "properties": {"Node name for S/R": "UMLViewerURL"},
            "widgets_values": [],
            "inputs": [{"name": "kroki_url", "type": "STRING", "link": link_id}],
        })
        links.append({
            "id": link_id,
            "origin_id": diagram_id,
            "origin_slot": 2,
            "target_id": viewer_id,
            "target_slot": 0,
            "type": "STRING",
        })

    # Plantuml: txt (diagram id 4, viewer id 8, link id 4)
    i = 3
    link_id = 4
    diagram_id = 4
    viewer_id = 8
    outputs = [dict(o) for o in outputs_template]
    outputs[2]["links"] = [link_id]
    nodes.append({
        "id": diagram_id,
        "type": "UMLDiagram",
        "class_type": "UMLDiagram",
        "pos": [100, base_y + i * row_height],
        "size": [400, 300],
        "flags": {},
        "order": i,
        "mode": 0,
        "outputs": outputs,
        "properties": {"Node name for S/R": "UMLDiagram"},
        "widgets_values": [
            0,
            "https://kroki.io",
            plantuml_idx,
            plantuml_code,
            format_string_to_widget_index("plantuml", "txt"),
        ],
        "inputs": [],
    })
    nodes.append({
        "id": viewer_id,
        "type": "UMLViewerURL",
        "class_type": "UMLViewerURL",
        "pos": [100, base_y + i * row_height + 320],
        "size": [280, 80],
        "flags": {},
        "order": 6,
        "mode": 0,
        "outputs": [
            {"name": "viewer_url", "type": "STRING", "links": None, "slot_index": 0, "shape": 3}
        ],
        "properties": {"Node name for S/R": "UMLViewerURL"},
        "widgets_values": [],
        "inputs": [{"name": "kroki_url", "type": "STRING", "link": link_id}],
    })
    links.append({
        "id": link_id,
        "origin_id": diagram_id,
        "origin_slot": 2,
        "target_id": viewer_id,
        "target_slot": 0,
        "type": "STRING",
    })

    wf = {
        "lastNodeId": 8,
        "lastLinkId": 4,
        "nodes": nodes,
        "links": links,
        "groups": [
            {
                "title": "Viewer formats test (URL, PNG, SVG, PDF, TXT)",
                "bound": [80, 80, 400, 1800],
                "nodes": [1, 2, 3, 4, 5, 6, 7, 8],
            }
        ],
        "config": {},
        "extra": {},
        "version": 0.4,
    }
    return normalize(wf)


def run_generate() -> int:
    _sync_js_supported_formats()
    _load_kroki_and_default_code()
    if _validate_default_code_coverage() != 0:
        return 1
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
        nodes.append(
            {
                "id": i + 1,
                "type": "UMLDiagram",
                "class_type": "UMLDiagram",
                "pos": [x, y],
                "size": [400, 300],
                "flags": {},
                "order": i,
                "mode": 0,
                "outputs": list(outputs),
                "properties": {"Node name for S/R": "UMLDiagram"},
                "widgets_values": [0, "https://kroki.io", i, code, fmt_idx],
            }
        )
        per_type = normalize(build_single_node_workflow(dtype, i))
        out_per = workflows_dir / f"uml_{dtype}.json"
        _write_workflow_json(out_per, per_type)
        logger.info("Wrote %s", out_per)

    # Single-node multi-format test: blockdiag SVG/PNG, plantuml TXT, each with viewer (URL, svg, png, txt)
    uml_single_node_wf = _build_uml_single_node_workflow()
    _write_workflow_json(workflows_dir / "uml_single_node.json", uml_single_node_wf)
    logger.info("Wrote %s", workflows_dir / "uml_single_node.json")

    groups = [
        {
            "title": "UML (PlantUML, Mermaid, GraphViz, D2, ERD, Nomnoml, UMLet)",
            "nodes": [17, 12, 11, 6, 9, 13, 24],
        },
        {"title": "Block / Sequence diagrams", "nodes": [1, 2, 19, 14, 15, 18]},
        {"title": "Data (DBML, Vega, Vega-Lite, WaveDrom)", "nodes": [7, 25, 26, 27]},
        {
            "title": "Other (BPMN, Bytefield, C4, Ditaa, Excalidraw, Pikchr, Structurizr, Svgbob, Symbolator, TikZ, WireViz)",
            "nodes": [3, 4, 5, 8, 10, 16, 20, 21, 22, 23, 28],
        },
    ]
    wf = normalize(
        {
            "lastNodeId": 28,
            "lastLinkId": 0,
            "nodes": nodes,
            "links": [],
            "groups": groups,
            "config": {},
            "extra": {},
            "version": 0.4,
        }
    )
    out_all = workflows_dir / "uml_all_diagrams.json"
    _write_workflow_json(out_all, wf)
    logger.info("Wrote %s", out_all)

    # Viewer formats test: multiple output formats (URL, PNG, SVG, PDF, TXT) for the diagram viewer
    viewer_formats_wf = _build_viewer_formats_test_workflow()
    out_viewer_formats = workflows_dir / "uml_viewer_formats_test.json"
    _write_workflow_json(out_viewer_formats, viewer_formats_wf)
    logger.info("Wrote %s", out_viewer_formats)

    # Write LLM Ollama workflow to workflows/
    llm_ollama = _build_llm_ollama_workflow()
    out_ollama = workflows_dir / "llm_ollama.json"
    _write_workflow_json(out_ollama, llm_ollama)
    logger.info("Wrote %s", out_ollama)
    return 0


def _build_llm_ollama_workflow() -> dict:
    """Build the LLM (Ollama) → Kroki workflow dict; normalized."""
    from nodes.llm_call import OLLAMA_MODELS

    default_ollama_model = OLLAMA_MODELS[0] if OLLAMA_MODELS else "llama3.2"
    wf = {
        "lastNodeId": 4,
        "lastLinkId": 4,
        "nodes": [
            {
                "id": 1,
                "type": "LLMPromptEngine",
                "pos": [100, 100],
                "size": [400, 320],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [],
                "outputs": [
                    {"name": "prompt", "type": "STRING", "links": [1], "slot_index": 0, "shape": 3},
                    {
                        "name": "positive",
                        "type": "STRING",
                        "links": None,
                        "slot_index": 1,
                        "shape": 3,
                    },
                    {
                        "name": "negative",
                        "type": "STRING",
                        "links": [2],
                        "slot_index": 2,
                        "shape": 3,
                    },
                ],
                "properties": {"Node name for S/R": "LLMPromptEngine"},
                "widgets_values": [
                    "Generate a Mermaid diagram that illustrates: {{description}}",
                    "Kroki – Creates diagrams from textual descriptions!",
                    "Output only valid Mermaid diagram code. No markdown fences (no ```). No explanation.",
                    "Do not add any text outside the diagram syntax.",
                    "kroki.txt",
                    "mermaid",
                    "svg",
                ],
            },
            {
                "id": 2,
                "type": "LLMCall",
                "pos": [560, 100],
                "size": [320, 200],
                "flags": {},
                "order": 1,
                "mode": 0,
                "inputs": [
                    {"name": "prompt", "type": "STRING", "link": 1},
                    {"name": "negative_prompt", "type": "STRING", "link": 2},
                ],
                "outputs": [
                    {"name": "text", "type": "STRING", "links": [3], "slot_index": 0, "shape": 3},
                ],
                "properties": {"Node name for S/R": "LLMCall"},
                "widgets_values": ["", "ollama", default_ollama_model, "", "", ""],
            },
            {
                "id": 3,
                "type": "UMLDiagram",
                "pos": [560, 360],
                "size": [400, 300],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [{"name": "code_input", "type": "*", "link": 3}],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": None, "slot_index": 0, "shape": 3},
                    {"name": "path", "type": "STRING", "links": None, "slot_index": 1, "shape": 3},
                    {
                        "name": "kroki_url",
                        "type": "STRING",
                        "links": [4],
                        "slot_index": 2,
                        "shape": 3,
                    },
                    {
                        "name": "content_for_viewer",
                        "type": "STRING",
                        "links": None,
                        "slot_index": 3,
                        "shape": 3,
                    },
                ],
                "properties": {"Node name for S/R": "UMLDiagram"},
                "widgets_values": [0, "https://kroki.io", 11, "", 1],
            },
            {
                "id": 4,
                "type": "UMLViewerURL",
                "pos": [560, 700],
                "size": [280, 80],
                "flags": {},
                "order": 3,
                "mode": 0,
                "inputs": [{"name": "kroki_url", "type": "STRING", "link": 4}],
                "outputs": [
                    {
                        "name": "viewer_url",
                        "type": "STRING",
                        "links": None,
                        "slot_index": 0,
                        "shape": 3,
                    },
                ],
                "properties": {"Node name for S/R": "UMLViewerURL"},
                "widgets_values": [],
            },
        ],
        "links": [
            {
                "id": 1,
                "origin_id": 1,
                "origin_slot": 0,
                "target_id": 2,
                "target_slot": 0,
                "type": "STRING",
            },
            {
                "id": 2,
                "origin_id": 1,
                "origin_slot": 2,
                "target_id": 2,
                "target_slot": 3,
                "type": "STRING",
            },
            {
                "id": 3,
                "origin_id": 2,
                "origin_slot": 0,
                "target_id": 3,
                "target_slot": 0,
                "type": "STRING",
            },
            {
                "id": 4,
                "origin_id": 3,
                "origin_slot": 2,
                "target_id": 4,
                "target_slot": 0,
                "type": "STRING",
            },
        ],
        "groups": [
            {"title": "LLM (Ollama) → Kroki", "bound": [80, 80, 900, 820], "nodes": [1, 2, 3, 4]},
        ],
        "config": {},
        "extra": {},
        "version": 0.4,
    }
    return normalize(wf)


def run_generate_and_normalize() -> int:
    """Generate workflows then normalize workflows/*.json in place."""
    run_generate()
    workflows_dir = root / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    to_normalize: list[Path] = []
    if workflows_dir.is_dir():
        to_normalize.extend(sorted(workflows_dir.glob("*.json")))
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


def _run_in_place_normalize() -> int:
    """Normalize workflows/*.json in place. Return 0."""
    workflows_dir = root / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    to_normalize: list[Path] = []
    if workflows_dir.is_dir():
        to_normalize.extend(sorted(workflows_dir.glob("*.json")))
    if not to_normalize:
        return 0

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


def run_full_pipeline() -> int:
    """Generate, normalize, add viewer to non-CPU workflows, normalize again, then check formats sync."""
    run_generate()
    _run_in_place_normalize()
    _run_add_viewer_to_workflows()
    _run_in_place_normalize()
    return _check_formats_sync()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate workflow JSON and optionally normalize.")
    subparsers = parser.add_subparsers(dest="command", help="command")
    subparsers.add_parser(
        "generate", help="Generate workflows then normalize workflows/*"
    )
    norm_parser = subparsers.add_parser("normalize", help="Only normalize given workflow JSON")
    norm_parser.set_defaults(_parser=norm_parser)
    norm_parser.add_argument(
        "input",
        nargs="*",
        default=[],
        help="Input JSON file(s); '-' for stdin. Omit to normalize workflows/ in place.",
    )
    norm_parser.add_argument("-o", "--output", default=None, help="Output file or directory")
    norm_parser.add_argument(
        "--indent", type=int, default=2, help="JSON indent (default 2); 0 for compact"
    )
    subparsers.add_parser(
        "sync-formats",
        help="Update web/ComfyUI-UML.js SUPPORTED_FORMATS from nodes/kroki_client.py only",
    )
    args = parser.parse_args(argv)
    if args.command == "normalize":
        return run_normalize(args)
    if args.command == "generate":
        return run_generate_and_normalize()
    if args.command == "sync-formats":
        return _sync_js_supported_formats()
    # Default: full pipeline (generate → normalize → add viewer → normalize → formats sync check)
    return run_full_pipeline()


if __name__ == "__main__":
    sys.exit(main())
