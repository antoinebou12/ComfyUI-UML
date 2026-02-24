"""
Workflow tools: generate diagram workflows, normalize ComfyUI workflow JSON,
add viewer nodes, and check format sync.

Default (no subcommand): full pipeline — generate workflows, normalize,
add UMLViewerURL to workflows that have UMLDiagram, normalize again,
then verify web/ComfyUI-UML.js SUPPORTED_FORMATS matches nodes/kroki_client.py
(exits 1 if they differ).

  python scripts/generate_all_diagrams_workflow.py
  → generate → normalize → add viewer → normalize → check formats sync

Generate only (no add-viewer, no sync check):

  python scripts/generate_all_diagrams_workflow.py generate
  → Writes workflows/uml_<type>.json and uml_all_diagrams.json, then normalizes
    them and any example_workflows/*.json

Normalize only (specific files or stdin):

  python scripts/generate_all_diagrams_workflow.py normalize
  → Normalizes workflows/*.json and example_workflows/*.json in place (no input = use these folders).

  python scripts/generate_all_diagrams_workflow.py normalize workflow.json -o fixed.json
  python scripts/generate_all_diagrams_workflow.py normalize -  (stdin → stdout)
  python scripts/generate_all_diagrams_workflow.py normalize workflows/*.json -o out_dir
"""

from __future__ import annotations

import argparse
import json
import logging
import math
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


def normalize(data: dict) -> dict:
    """Return a normalized copy of the workflow (links, groups, root keys)."""
    if not data or not isinstance(data, dict):
        return data

    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
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

    # No input → normalize workflows/ and example_workflows/ in place
    if not inputs:
        workflows_dir = root / "workflows"
        example_dir = root / "example_workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        example_dir.mkdir(parents=True, exist_ok=True)
        to_normalize: list[Path] = []
        if workflows_dir.is_dir():
            to_normalize.extend(sorted(workflows_dir.glob("*.json")))
        if example_dir.is_dir():
            to_normalize.extend(sorted(example_dir.glob("*.json")))
        if not to_normalize:
            logger.info("No JSON files in workflows/ or example_workflows/.")
            return 0
        logger.info(
            "Normalizing workflows/ and example_workflows/ in place (%d file(s)).",
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
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            logger.info("Wrote %s", args.output)
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
            logger.info("Wrote %s", dest)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            logger.info("Normalized %s", path)
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
        nodes.append(
            {
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
            }
        )
        per_type = normalize(build_single_node_workflow(dtype, i))
        out_per = workflows_dir / f"uml_{dtype}.json"
        with open(out_per, "w", encoding="utf-8") as f:
            json.dump(per_type, f, indent=2)
        logger.info("Wrote %s", out_per)
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
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)
    logger.info("Wrote %s", out_all)

    # Write LLM Ollama workflow to workflows/ and example_workflows/
    example_dir = root / "example_workflows"
    example_dir.mkdir(parents=True, exist_ok=True)
    llm_ollama = _build_llm_ollama_workflow()
    for dest_dir in (workflows_dir, example_dir):
        out_ollama = dest_dir / "llm_ollama.json"
        with open(out_ollama, "w", encoding="utf-8") as f:
            json.dump(llm_ollama, f, indent=2)
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
                "target_slot": 4,
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
    """Generate workflows then normalize workflows/*.json and example_workflows/*.json in place."""
    run_generate()
    workflows_dir = root / "workflows"
    example_dir = root / "example_workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    example_dir.mkdir(parents=True, exist_ok=True)
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


def _run_in_place_normalize() -> int:
    """Normalize workflows/*.json and example_workflows/*.json in place. Return 0."""
    workflows_dir = root / "workflows"
    example_dir = root / "example_workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    example_dir.mkdir(parents=True, exist_ok=True)
    to_normalize: list[Path] = []
    if workflows_dir.is_dir():
        to_normalize.extend(sorted(workflows_dir.glob("*.json")))
    if example_dir.is_dir():
        to_normalize.extend(sorted(example_dir.glob("*.json")))
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
    """Generate, normalize, add viewer to all workflows, normalize again, then check formats sync."""
    run_generate()
    _run_in_place_normalize()
    import add_viewer_to_workflows  # noqa: E402

    add_viewer_to_workflows.main()
    _run_in_place_normalize()
    import check_formats_sync  # noqa: E402

    return check_formats_sync.main()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate workflow JSON and optionally normalize.")
    subparsers = parser.add_subparsers(dest="command", help="command")
    subparsers.add_parser(
        "generate", help="Generate workflows then normalize workflows/* and example_workflows/*"
    )
    norm_parser = subparsers.add_parser("normalize", help="Only normalize given workflow JSON")
    norm_parser.set_defaults(_parser=norm_parser)
    norm_parser.add_argument(
        "input",
        nargs="*",
        default=[],
        help="Input JSON file(s); '-' for stdin. Omit to normalize workflows/ and example_workflows/ in place.",
    )
    norm_parser.add_argument("-o", "--output", default=None, help="Output file or directory")
    norm_parser.add_argument(
        "--indent", type=int, default=2, help="JSON indent (default 2); 0 for compact"
    )
    args = parser.parse_args(argv)
    if args.command == "normalize":
        return run_normalize(args)
    if args.command == "generate":
        return run_generate_and_normalize()
    # Default: full pipeline (generate → normalize → add viewer → normalize → formats sync check)
    return run_full_pipeline()


if __name__ == "__main__":
    sys.exit(main())
