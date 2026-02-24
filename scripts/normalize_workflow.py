"""
Normalize ComfyUI workflow JSON for reliable load and Queue Prompt.

Fixes:
- Corrupted or array-style links -> object-style links rebuilt from node inputs/outputs
- Groups missing or invalid bound -> bound computed from node positions
- Root keys last_node_id / last_link_id -> lastNodeId / lastLinkId (camelCase)

Usage:
  python scripts/normalize_workflow.py workflow.json -o fixed.json
  python scripts/normalize_workflow.py -o fixed.json < workflow.json
  python scripts/normalize_workflow.py workflow.json   # prints to stdout
  python scripts/normalize_workflow.py w1.json w2.json   # normalize in-place
  python scripts/normalize_workflow.py workflows/*.json -o out_dir   # write to directory
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _is_links_corrupted(links: list) -> bool:
    """True if links should be rebuilt (empty, array-style, or all-null entries)."""
    if not isinstance(links, list):
        return True
    if len(links) == 0:
        return False  # empty is valid
    first = links[0]
    if isinstance(first, list):
        return True  # array-style [id, origin, ...]
    if isinstance(first, dict):
        # Check for required keys; if any entry is all-null-like, consider corrupted
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
    id_to_origin: dict[int, tuple[int, int, str]] = {}  # link_id -> (node_id, slot_index, type)
    id_to_target: dict[int, tuple[int, int]] = {}       # link_id -> (node_id, slot_index)

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
    """In-place: set bound on each group if missing or invalid. Uses node positions."""
    node_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id") is not None}

    for g in groups:
        if not isinstance(g, dict):
            continue
        bound = g.get("bound")
        if isinstance(bound, (list, tuple)) and len(bound) >= 4:
            try:
                [float(bound[0]), float(bound[1]), float(bound[2]), float(bound[3])]
                continue  # valid
            except (TypeError, ValueError):
                pass
        # Compute from nodes in group
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
    data = json.loads(json.dumps(data))  # deep copy

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
        data["nodes"] = nodes

    # Rebuild links if corrupted
    links = data.get("links")
    if not isinstance(links, list) or _is_links_corrupted(links):
        links = _rebuild_links(nodes)
        data["links"] = links

    # lastLinkId / last_node_id (prefer max link id when links were rebuilt or missing)
    last_link = data.get("lastLinkId") if data.get("lastLinkId") is not None else data.get("last_link_id")
    if links and (last_link is None or last_link == 0):
        last_link = max(L.get("id", 0) for L in links if isinstance(L, dict))
    if last_link is not None:
        data["lastLinkId"] = int(last_link)
    for key in ("last_link_id",):
        data.pop(key, None)

    # lastNodeId / last_node_id
    last_node = data.get("lastNodeId") or data.get("last_node_id")
    if last_node is None and nodes:
        last_node = max(n.get("id", 0) for n in nodes if isinstance(n, dict))
    if last_node is not None:
        data["lastNodeId"] = int(last_node)
    for key in ("last_node_id",):
        data.pop(key, None)

    # Ensure groups have valid bound
    groups = data.get("groups")
    if isinstance(groups, list):
        _ensure_group_bounds(groups, nodes)

    # Ensure standard root keys exist for a valid workflow
    if "config" not in data:
        data["config"] = {}
    if "extra" not in data:
        data["extra"] = {}
    if "version" not in data:
        data["version"] = 0.4

    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize ComfyUI workflow JSON for reliable load and Queue Prompt.",
    )
    parser.add_argument(
        "input",
        nargs="*",
        default=["-"],
        help="Input JSON file path(s); use '-' for stdin (single only)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON file or directory; with multiple inputs use a directory",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent (default 2); 0 for compact",
    )
    args = parser.parse_args()

    inputs = args.input if isinstance(args.input, list) else [args.input]
    if not inputs or (len(inputs) == 1 and inputs[0] == "-"):
        inputs = ["-"] if not inputs or inputs[0] == "-" else inputs

    # Expand glob patterns (Windows PowerShell does not expand workflows/*.json)
    def expand_globs(path_list: list) -> list:
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

    inputs = expand_globs(inputs)

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

    # Multiple files or single file path
    out_path = Path(args.output) if args.output else None
    if len(inputs) > 1 and out_path is not None and not out_path.is_dir():
        parser.error("with multiple inputs, -o must be a directory or omitted (in-place)")

    if len(inputs) > 1 and out_path is not None:
        out_path.mkdir(parents=True, exist_ok=True)

    for inp in inputs:
        if inp == "-":
            continue
        path = Path(inp)
        if not path.is_file():
            parser.error(f"not a file: {path}")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        out = normalize(raw)
        if out_path is not None:
            if out_path.is_dir():
                dest = out_path / path.name
            else:
                dest = out_path
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            print("Wrote", dest)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=args.indent or None, ensure_ascii=False)
            print("Normalized", path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
