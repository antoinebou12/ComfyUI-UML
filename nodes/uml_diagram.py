"""
UML diagram node: render diagram source to IMAGE + save path.
"""

import io
import os
import time

import numpy as np
import torch
from PIL import Image

from kroki_client import DIAGRAM_TYPES, KrokiError, render

# Default example code per diagram type (minimal runnable example)
DEFAULT_CODE: dict[str, str] = {
    "mermaid": "graph TD\n    A[Start] --> B[End]",
    "plantuml": "@startuml\nAlice -> Bob: hello\n@enduml",
    "graphviz": "digraph G { A -> B; }",
    "d2": "x -> y: label",
    "blockdiag": "blockdiag { A -> B; }",
    "seqdiag": "seqdiag { a -> b: msg; }",
    "actdiag": "actdiag { write -> convert -> image; }",
    "nwdiag": 'nwdiag { network { address = "10.0.0.0/24"; } }',
    "c4plantuml": "!include <C4/C4_Context>\nPerson(user)\nSystem(sys)\nRel(user, sys, Uses)",
    "erd": "[User]\n*id\nname\n--\n[Order]\n*id\nuser_id\nUser *-- Order",
    "vegalite": '{"mark":"bar","encoding":{"x":{"field":"a","type":"quantitative"},"y":{"field":"b","type":"quantitative"}},"data":{"values":[{"a":1,"b":2}]}}',
    "wavedrom": '{ "signal": [ { "name": "clk", "wave": "p...." } ] }',
}


def _get_default_code(diagram_type: str) -> str:
    return DEFAULT_CODE.get(
        diagram_type.lower().strip(),
        "// Enter your diagram source here",
    )


def _png_bytes_to_tensor(png_bytes: bytes) -> torch.Tensor:
    """Convert PNG bytes to ComfyUI IMAGE tensor [1, H, W, 3] in 0-1 range."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None, ...]
    return tensor


def _placeholder_tensor() -> torch.Tensor:
    """Return a tiny placeholder image [1, 1, 1, 3] for SVG-only output."""
    return torch.zeros(1, 1, 1, 3, dtype=torch.float32)


class UMLDiagram:
    """Render diagram source (Mermaid, PlantUML, etc.) to IMAGE and save file."""

    CATEGORY = "UML"
    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "run"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backend": (["web", "local"], {"default": "web"}),
                "kroki_url": ("STRING", {"default": "https://kroki.io"}),
                "diagram_type": (DIAGRAM_TYPES, {"default": "mermaid"}),
                "code": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": _get_default_code("mermaid"),
                    },
                ),
            },
            "optional": {
                "output_format": (["png", "svg"], {"default": "png"}),
            },
        }

    def run(
        self,
        backend: str,
        kroki_url: str,
        diagram_type: str,
        code: str,
        output_format: str = "png",
    ):
        if not (code or "").strip():
            code = _get_default_code(diagram_type)

        try:
            data = render(
                kroki_url=kroki_url,
                diagram_type=diagram_type,
                diagram_source=code,
                output_format=output_format,
                backend=backend,
            )
        except KrokiError as e:
            raise RuntimeError(str(e)) from e

        # Save to ComfyUI output directory
        try:
            folder_paths = __import__("folder_paths", fromlist=["get_output_directory"])
            output_dir = folder_paths.get_output_directory()
        except Exception:
            output_dir = os.path.expanduser("~/ComfyUI/output")
            os.makedirs(output_dir, exist_ok=True)

        subdir = os.path.join(output_dir, "uml")
        os.makedirs(subdir, exist_ok=True)
        ext = "png" if output_format == "png" else "svg"
        safe_type = diagram_type.replace("/", "_")[:20]
        filename = f"uml_{safe_type}_{int(time.time() * 1000)}.{ext}"
        filepath = os.path.join(subdir, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        # IMAGE output: decode PNG to tensor; for SVG return placeholder
        if output_format == "png" and data[:8] == b"\x89PNG\r\n\x1a\n":
            image_tensor = _png_bytes_to_tensor(data)
        else:
            image_tensor = _placeholder_tensor()

        return (image_tensor, filepath)
