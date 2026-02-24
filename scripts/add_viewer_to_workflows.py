"""
Add Diagram Viewer URL node to every workflow that has UMLDiagram but not yet UMLViewerURL.
Also ensures every UMLDiagram node has the fourth output (content_for_viewer).
Run from repo root: python scripts/add_viewer_to_workflows.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent


def has_viewer_node(nodes: list) -> bool:
    return any(n and n.get("type") == "UMLViewerURL" for n in nodes)


def ensure_uml_outputs(node: dict) -> bool:
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


def first_uml_diagram_id(nodes: list) -> int | None:
    for n in nodes or []:
        if n and n.get("type") == "UMLDiagram":
            return n.get("id")
    return None


def max_node_id(nodes: list) -> int:
    m = 0
    for n in nodes or []:
        if n and isinstance(n.get("id"), (int, float)):
            m = max(m, int(n["id"]))
    return m


def max_link_id(links: list) -> int:
    m = 0
    for L in links or []:
        if L and isinstance(L.get("id"), (int, float)):
            m = max(m, int(L["id"]))
    return m


def add_viewer_to_workflow(data: dict) -> bool:
    """Mutate data: add UMLViewerURL and link from first UMLDiagram. Return True if changed."""
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return False

    # Ensure all UML nodes have 4 outputs (content_for_viewer)
    any_uml_updated = any(ensure_uml_outputs(n) for n in nodes)

    if has_viewer_node(nodes):
        return any_uml_updated

    first_uml_id = first_uml_diagram_id(nodes)
    if first_uml_id is None:
        return any_uml_updated

    # Ensure all UML nodes have 4 outputs (already done above)

    new_node_id = max_node_id(nodes) + 1
    new_link_id = max_link_id(data.get("links")) + 1

    # Set first UML's kroki_url to link to new node
    for n in nodes:
        if n and n.get("id") == first_uml_id:
            for o in n.get("outputs") or []:
                if o and o.get("name") == "kroki_url":
                    o["links"] = [new_link_id]
                    break
            break

    # Viewer node position: below first UML
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

    # Add to first group if any
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


def main() -> int:
    workflows_dir = root / "workflows"
    example_dir = root / "example_workflows"
    changed = 0
    for d in (workflows_dir, example_dir):
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Skip {path}: {e}", file=sys.stderr)
                continue
            if add_viewer_to_workflow(data):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Updated {path}")
                changed += 1
    print(f"Done. Updated {changed} workflow(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
