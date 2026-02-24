"""
UML diagram node: render diagram source to IMAGE + save path.
"""

import io
import json
import os
import time

import numpy as np
import torch
from PIL import Image

from .kroki_client import (
    DIAGRAM_TYPES,
    KrokiError,
    SUPPORTED_FORMATS,
    get_kroki_url,
    render,
)

from .default_code import get_default_code

def _normalize_to_code(value: object) -> str:
    """Normalize LLM/text output to diagram source string.
    Handles str, tuple/list (first element), and objects with text-like attributes.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (tuple, list)) and len(value):
        return _normalize_to_code(value[0])
    for attr in ("text", "assistant_response", "content", "output"):
        if hasattr(value, attr):
            v = getattr(value, attr)
            if v is not None and isinstance(v, str):
                return v.strip()
    return str(value).strip()


def _placeholder_tensor() -> torch.Tensor:
    """Return a tiny placeholder image [1, 1, 1, 3] for non-raster output (SVG, PDF, etc.)."""
    return torch.zeros(1, 1, 1, 3, dtype=torch.float32)


def _svg_bytes_to_tensor(svg_bytes: bytes) -> torch.Tensor | None:
    """Convert SVG bytes to ComfyUI IMAGE tensor using cairosvg if available. Returns None on failure."""
    if not svg_bytes or not svg_bytes.lstrip().startswith((b"<?xml", b"<svg")):
        return None
    try:
        import cairosvg
        png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
        if png_bytes and len(png_bytes) >= 8 and png_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return _raster_bytes_to_tensor(png_bytes)
    except Exception:
        pass
    return None


def _raster_bytes_to_tensor(data: bytes) -> torch.Tensor:
    """Convert PNG or JPEG bytes to ComfyUI IMAGE tensor [1, H, W, 3] in 0-1 range."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


class UMLDiagram:
    """Render diagram source (Mermaid, PlantUML, etc.) to IMAGE and save file."""

    CATEGORY = "UML"
    SEARCH_ALIASES = ["uml", "mermaid", "plantuml", "diagram", "kroki", "render"]
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "path", "kroki_url", "content_for_viewer")
    FUNCTION = "run"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backend": (["web", "local"], {"default": "web"}),
                "kroki_url": (
                    "STRING",
                    {"default": "https://kroki.io", "visible_when": {"backend": ["web"]}},
                ),
                "diagram_type": (DIAGRAM_TYPES, {"default": "mermaid"}),
                "code": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": get_default_code("mermaid"),
                    },
                ),
            },
            "optional": {
                "code_input": ("*", {}),  # When connected, overrides code widget (e.g. from any LLM output node)
                "output_format": (["png", "svg", "jpeg", "pdf", "txt", "base64"], {"default": "png"}),
                "diagram_options": (
                    "STRING",
                    {"default": "", "multiline": False, "visible_when": {"backend": ["web"]}},
                ),
                "theme": (
                    "STRING",
                    {"default": "", "multiline": False, "visible_when": {"backend": ["local"]}},
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, diagram_type=None, output_format=None):
        # Only constant (widget) values are passed; format vs diagram_type is also validated in run().
        if diagram_type is None or output_format is None:
            return True
        if not isinstance(diagram_type, str) or not isinstance(output_format, str):
            return True
        key = diagram_type.lower().strip()
        allowed = SUPPORTED_FORMATS.get(key, ["png", "svg"])
        if output_format.lower().strip() in allowed:
            return True
        return f"Format '{output_format}' not supported for {diagram_type}. Allowed: {', '.join(allowed)}"

    def run(
        self,
        backend: str,
        kroki_url: str,
        diagram_type: str,
        code: str,
        output_format: str = "png",
        diagram_options: str = "",
        theme: str = "",
        code_input=None,
        unique_id=None,
        prompt=None,
    ):
        if code_input is not None:
            code = _normalize_to_code(code_input)
        if not (code or "").strip():
            code = get_default_code(diagram_type)

        diagram_type_key = diagram_type.lower().strip()
        allowed_formats = SUPPORTED_FORMATS.get(diagram_type_key, ["png", "svg"])
        if output_format.lower().strip() not in allowed_formats:
            raise RuntimeError(
                f"Format '{output_format}' not supported for {diagram_type}. "
                f"Allowed: {', '.join(allowed_formats)}"
            )

        options = None
        if (diagram_options or "").strip():
            try:
                options = json.loads(diagram_options)
                if not isinstance(options, dict):
                    options = None
            except json.JSONDecodeError:
                options = None

        theme_val = (theme or "").strip() or None

        def _send_progress(value: int, max_val: int = 1) -> None:
            # Progress payload: node is required; prompt_id included when provided by executor (see Messages docs).
            if unique_id is None:
                return
            try:
                from server import PromptServer
                if getattr(PromptServer, "instance", None) is None:
                    return
                payload = {"node": unique_id, "value": value, "max": max_val}
                prompt_id = None
                if prompt is not None:
                    if isinstance(prompt, dict) and "prompt_id" in prompt:
                        prompt_id = prompt["prompt_id"]
                    elif isinstance(prompt, (list, tuple)) and len(prompt):
                        prompt_id = prompt[0]
                if prompt_id is not None:
                    payload["prompt_id"] = prompt_id
                PromptServer.instance.send_sync("progress", payload)
            except Exception:
                pass

        _send_progress(0, 1)
        try:
            data = render(
                kroki_url=kroki_url,
                diagram_type=diagram_type,
                diagram_source=code,
                output_format=output_format,
                backend=backend,
                theme=theme_val,
                diagram_options=options,
            )
        except KrokiError as e:
            raise RuntimeError(f"Kroki error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Kroki error: {e}") from e
        finally:
            _send_progress(1, 1)

        # Shareable Kroki GET URL (same format as JS pako)
        kroki_url_out = get_kroki_url(
            kroki_url=kroki_url,
            diagram_type=diagram_type,
            diagram_source=code,
            output_format=output_format,
            diagram_options=options,
        )

        # Save to ComfyUI output directory
        try:
            folder_paths = __import__("folder_paths", fromlist=["get_output_directory"])
            output_dir = folder_paths.get_output_directory()
        except Exception as e:
            output_dir = os.path.expanduser("~/ComfyUI/output")
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as err:
                raise RuntimeError(f"Failed to create output directory: {err}") from err

        subdir = os.path.join(output_dir, "uml")
        try:
            os.makedirs(subdir, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create output/uml directory: {e}") from e

        ext_map = {"png": "png", "svg": "svg", "jpeg": "jpeg", "pdf": "pdf", "txt": "txt", "base64": "txt"}
        ext = ext_map.get(output_format, "png")
        if output_format == "base64" and len(data) >= 8:
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                ext = "png"
            elif data.lstrip().startswith((b"<?xml", b"<svg")):
                ext = "svg"
        safe_type = diagram_type.replace("/", "_")[:20]
        filename = f"uml_{safe_type}_{int(time.time() * 1000)}.{ext}"
        filepath = os.path.join(subdir, filename)
        try:
            with open(filepath, "wb") as f:
                f.write(data)
        except OSError as e:
            raise RuntimeError(f"Failed to write diagram to output/uml: {e}") from e

        # IMAGE output: raster (png/jpeg), SVG via cairosvg, or placeholder
        if output_format == "png" and len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
            image_tensor = _raster_bytes_to_tensor(data)
        elif output_format == "jpeg" and len(data) >= 2 and data[:2] == b"\xff\xd8":
            image_tensor = _raster_bytes_to_tensor(data)
        elif output_format == "svg" and data.lstrip().startswith((b"<?xml", b"<svg")):
            image_tensor = _svg_bytes_to_tensor(data) or _placeholder_tensor()
        else:
            image_tensor = _placeholder_tensor()

        # content_for_viewer: raw SVG string for ComfyUI_Viewer, else path or kroki_url
        if output_format == "svg" and data.lstrip().startswith((b"<?xml", b"<svg")):
            content_for_viewer = data.decode("utf-8", errors="replace")
        else:
            content_for_viewer = filepath

        return (image_tensor, filepath, kroki_url_out, content_for_viewer)
