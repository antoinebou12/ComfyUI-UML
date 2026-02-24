"""
Kroki client for ComfyUI-UML: web API (POST/GET) and optional local renderers.
"""

import base64
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import zlib
from typing import Any, Optional

# Try httpx first, fall back to requests
try:
    import httpx

    _USE_HTTPX = True
except ImportError:
    _USE_HTTPX = False

# Diagram types supported by Kroki (subset that supports png and/or svg)
# See https://docs.kroki.io/kroki/diagram-types
DIAGRAM_TYPES = [
    "actdiag",
    "blockdiag",
    "bpmn",
    "bytefield",
    "c4plantuml",
    "d2",
    "dbml",
    "ditaa",
    "erd",
    "excalidraw",
    "graphviz",
    "mermaid",
    "nomnoml",
    "nwdiag",
    "packetdiag",
    "pikchr",
    "plantuml",
    "rackdiag",
    "seqdiag",
    "structurizr",
    "svgbob",
    "symbolator",
    "tikz",
    "umlet",
    "vega",
    "vegalite",
    "wavedrom",
    "wireviz",
]

# Output formats per diagram type (common ones: png, svg)
# Types that only support SVG: bpmn, bytefield, excalidraw, nomnoml, pikchr, svgbob, symbolator
# D2 supports PNG as well per Kroki / JS clients
SUPPORTED_FORMATS: dict[str, list[str]] = {
    "actdiag": ["png", "svg", "pdf"],
    "blockdiag": ["png", "svg", "pdf"],
    "bpmn": ["svg"],
    "bytefield": ["svg"],
    "c4plantuml": ["png", "svg", "pdf", "txt", "base64"],
    "d2": ["png", "svg"],
    "dbml": ["svg"],
    "ditaa": ["png", "svg"],
    "erd": ["png", "svg", "jpeg", "pdf"],
    "excalidraw": ["svg"],
    "graphviz": ["png", "svg", "pdf", "jpeg"],
    "mermaid": ["svg", "png", "base64"],
    "nomnoml": ["svg"],
    "nwdiag": ["png", "svg", "pdf"],
    "packetdiag": ["png", "svg", "pdf"],
    "pikchr": ["svg"],
    "plantuml": ["png", "svg", "pdf", "txt", "base64"],
    "rackdiag": ["png", "svg", "pdf"],
    "seqdiag": ["png", "svg", "pdf"],
    "structurizr": ["png", "svg", "pdf", "txt", "base64"],
    "svgbob": ["svg"],
    "symbolator": ["svg"],
    "tikz": ["png", "svg", "jpeg", "pdf"],
    "umlet": ["png", "svg", "jpeg"],
    "vega": ["png", "svg", "pdf"],
    "vegalite": ["png", "svg", "pdf"],
    "wavedrom": ["svg"],
    "wireviz": ["png", "svg"],
}


class KrokiError(Exception):
    """Raised when Kroki request or local render fails."""

    pass


def _validate_type_format(diagram_type: str, output_format: str) -> None:
    """Raise if type or format is not supported."""
    diagram_type = diagram_type.lower().strip()
    output_format = output_format.lower().strip()
    if diagram_type not in SUPPORTED_FORMATS:
        raise KrokiError(
            f"Unsupported diagram type: {diagram_type}. "
            f"Supported: {', '.join(sorted(DIAGRAM_TYPES))}"
        )
    allowed = SUPPORTED_FORMATS[diagram_type]
    if output_format not in allowed:
        raise KrokiError(
            f"Format '{output_format}' not supported for {diagram_type}. "
            f"Supported: {', '.join(allowed)}"
        )


def _decode_base64_response(output_format: str, content: bytes) -> bytes:
    """If Kroki returned base64-encoded body, decode to raw bytes."""
    if output_format != "base64" or not content:
        return content
    try:
        return base64.b64decode(content)
    except Exception:
        return content


def _options_to_query(options: dict[str, Any]) -> str:
    """Build query string from diagram_options for GET requests. Flag options use empty value."""
    if not options:
        return ""
    parts = []
    for k, v in options.items():
        if v is True or v == "":
            parts.append((k, ""))
        else:
            parts.append((k, str(v)))
    qs = urllib.parse.urlencode(parts)
    return "?" + qs if qs else ""


def render_web(
    kroki_url: str,
    diagram_type: str,
    diagram_source: str,
    output_format: str,
    timeout: float = 30.0,
    diagram_options: Optional[dict[str, Any]] = None,
) -> bytes:
    """
    Render diagram via Kroki web API.
    Prefers POST plain text; when diagram_options is set, uses POST JSON body with
    diagram_options so Kroki can pass options to the engine (e.g. GraphViz scale,
    BlockDiag antialias, Mermaid/PlantUML/D2 theme). See Kroki diagram options docs.
    """
    _validate_type_format(diagram_type, output_format)
    base_url = kroki_url.rstrip("/")
    diagram_type = diagram_type.lower().strip()
    output_format = output_format.lower().strip()
    options = diagram_options or {}

    if options:
        # POST with JSON body so we can send diagram_options
        body = {"diagram_source": diagram_source, "diagram_options": options}
        if _USE_HTTPX:
            try:
                with httpx.Client(timeout=timeout) as client:
                    r = client.post(
                        f"{base_url}/{diagram_type}/{output_format}",
                        json=body,
                    )
                    r.raise_for_status()
                    return _decode_base64_response(output_format, r.content)
            except httpx.HTTPStatusError as e:
                raise KrokiError(f"Kroki HTTP {e.response.status_code}: {e.response.text[:200]}")
            except httpx.RequestError as e:
                raise KrokiError(f"Kroki request failed: {e}")
        else:
            try:
                import requests

                r = requests.post(
                    f"{base_url}/{diagram_type}/{output_format}",
                    json=body,
                    timeout=timeout,
                )
                r.raise_for_status()
                return _decode_base64_response(output_format, r.content)
            except Exception as e:
                raise KrokiError(f"Kroki request failed: {e}")

    # Plain text POST
    source_bytes = diagram_source.encode("utf-8")
    post_url = f"{base_url}/{diagram_type}/{output_format}"
    if _USE_HTTPX:
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.post(
                    post_url,
                    content=source_bytes,
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                )
                r.raise_for_status()
                return _decode_base64_response(output_format, r.content)
        except httpx.HTTPStatusError as e:
            raise KrokiError(f"Kroki HTTP {e.response.status_code}: {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise KrokiError(f"Kroki request failed: {e}")
    else:
        try:
            import requests

            r = requests.post(
                post_url,
                data=source_bytes,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=timeout,
            )
            r.raise_for_status()
            return _decode_base64_response(output_format, r.content)
        except Exception as e:
            raise KrokiError(f"Kroki request failed: {e}")


def _deflate_and_encode(text: str) -> str:
    """Compress with zlib and base64url-encode for GET URL."""
    if not text:
        return ""
    compressed = zlib.compress(text.encode("utf-8"), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return encoded.replace("+", "-").replace("/", "_")


def get_kroki_url(
    kroki_url: str,
    diagram_type: str,
    diagram_source: str,
    output_format: str,
    diagram_options: Optional[dict[str, Any]] = None,
) -> str:
    """
    Build shareable Kroki GET URL (deflate+base64url). Same format as JavaScript (pako)
    so URLs are interchangeable. Optional diagram_options are appended as query params.
    """
    _validate_type_format(diagram_type, output_format)
    base_url = kroki_url.rstrip("/")
    diagram_type = diagram_type.lower().strip()
    output_format = output_format.lower().strip()
    encoded = _deflate_and_encode(diagram_source)
    query = _options_to_query(diagram_options or {})
    return f"{base_url}/{diagram_type}/{output_format}/{encoded}{query}"


def render_local(
    diagram_type: str,
    diagram_source: str,
    output_format: str,
    theme: Optional[str] = None,
) -> Optional[bytes]:
    """
    Render locally if a renderer is available (e.g. graphviz, beautiful-mermaid for mermaid).
    Returns None to fall back to web.
    """
    diagram_type = diagram_type.lower().strip()
    output_format = output_format.lower().strip()

    if diagram_type == "graphviz" and output_format in ("png", "svg", "pdf", "jpeg"):
        try:
            import graphviz

            fmt = "png" if output_format == "png" else output_format
            src = graphviz.Source(diagram_source)
            return src.pipe(format=fmt)
        except Exception:
            return None

    if diagram_type == "mermaid" and output_format in ("svg", "png"):
        return _render_local_mermaid(diagram_source, output_format, theme)

    return None


def _script_dir() -> str:
    """Plugin root directory (parent of this package); scripts/ lives here."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _render_local_mermaid(
    diagram_source: str,
    output_format: str,
    theme: Optional[str] = None,
) -> Optional[bytes]:
    """
    Render Mermaid via local beautiful-mermaid Node script.
    Returns SVG or PNG bytes, or None if Node/script/cairosvg unavailable.
    """
    node_exe = shutil.which("node")
    if not node_exe:
        return None
    script_path = os.path.join(_script_dir(), "scripts", "render_mermaid.mjs")
    if not os.path.isfile(script_path):
        return None
    node_modules = os.path.join(_script_dir(), "scripts", "node_modules", "beautiful-mermaid")
    if not os.path.isdir(node_modules):
        return None

    env = os.environ.copy()
    if theme:
        env["BEAUTIFUL_MERMAID_THEME"] = theme

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".mmd",
        delete=False,
        encoding="utf-8",
    ) as f:
        tmp_path = f.name
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(diagram_source)
        result = subprocess.run(
            [node_exe, script_path, tmp_path],
            capture_output=True,
            timeout=60,
            cwd=os.path.join(_script_dir(), "scripts"),
            env=env,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if result.returncode != 0:
        return None
    svg_bytes = result.stdout
    if not svg_bytes or (
        not svg_bytes.lstrip().startswith(b"<?xml") and not svg_bytes.lstrip().startswith(b"<svg")
    ):
        return None

    if output_format == "svg":
        return svg_bytes

    # PNG: convert SVG to PNG
    try:
        import cairosvg

        return cairosvg.svg2png(bytestring=svg_bytes)
    except Exception:
        return None


def render(
    kroki_url: str,
    diagram_type: str,
    diagram_source: str,
    output_format: str,
    backend: str = "web",
    timeout: float = 30.0,
    theme: Optional[str] = None,
    diagram_options: Optional[dict[str, Any]] = None,
) -> bytes:
    """
    Render diagram: try local if backend=='local', else use web.
    theme: optional for local Mermaid (beautiful-mermaid theme name).
    diagram_options: optional dict passed to Kroki (e.g. scale for GraphViz, theme for D2/PlantUML,
    antialias for BlockDiag). See https://docs.kroki.io/kroki/setup/diagram-options/
    """
    if backend == "local":
        data = render_local(diagram_type, diagram_source, output_format, theme=theme)
        if data is not None:
            return data
        # Fall back to web
    return render_web(
        kroki_url, diagram_type, diagram_source, output_format, timeout, diagram_options
    )
