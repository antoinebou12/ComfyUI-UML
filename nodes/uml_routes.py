"""ComfyUI-UML API: save diagram, Ollama get_models, proxy diagram URLs."""

import os
import time
from urllib.parse import urlparse

try:
    from server import PromptServer
    from aiohttp import web
except ImportError:
    PromptServer = None
    web = None

try:
    import httpx
except ImportError:
    httpx = None

ALLOWED_MIME = frozenset({"image/png", "image/svg+xml", "image/jpeg"})
MIME_TO_EXT = {"image/png": "png", "image/svg+xml": "svg", "image/jpeg": "jpeg"}
MAX_FILENAME_LEN = 200
OLLAMA_GET_MODELS_DEFAULT_URL = "http://127.0.0.1:11434"
PROXY_ALLOWED_NETLOCS = frozenset({"kroki.io", "www.kroki.io"})
PROXY_TIMEOUT = 30.0


def _get_uml_output_dir():
    try:
        import folder_paths
        output_dir = folder_paths.get_output_directory()
    except Exception:
        output_dir = os.path.expanduser("~/ComfyUI/output")
    subdir = os.path.join(output_dir, "uml")
    os.makedirs(subdir, exist_ok=True)
    return subdir


def _safe_ext(mime_type: str | None, filename: str | None) -> str:
    if mime_type and mime_type in MIME_TO_EXT:
        return MIME_TO_EXT[mime_type]
    if filename:
        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        if ext in ("png", "svg", "jpeg", "jpg"):
            return "png" if ext == "jpg" else ext
    return "png"


def _json_err(msg: str, status: int = 400):
    return web.json_response({"error": msg}, status=status)


def _read_uploaded_file(file_field):
    """Return (body, filename, content_type). Raises on read failure."""
    if hasattr(file_field, "file"):
        body = file_field.file.read()
    else:
        body = file_field.read() if callable(getattr(file_field, "read", None)) else bytes(file_field)
    return (body, getattr(file_field, "filename", "") or "", getattr(file_field, "content_type", "") or "")


async def _ollama_get_models_handler(request):
    if request.method != "POST":
        return _json_err("Method not allowed", 405)
    if httpx is None:
        return _json_err("httpx not available", 503)
    try:
        data = await request.json()
    except Exception as e:
        return _json_err(str(e))
    url = (data.get("url") or OLLAMA_GET_MODELS_DEFAULT_URL).strip().rstrip("/") or OLLAMA_GET_MODELS_DEFAULT_URL
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{url}/api/tags")
            r.raise_for_status()
            models_raw = r.json().get("models") or []
    except httpx.HTTPStatusError as e:
        return _json_err(f"Ollama returned {e.response.status_code}", 502)
    except Exception as e:
        return _json_err(str(e), 502)

    models = [
        str(m.get("model") or m.get("name")) if isinstance(m, dict) and (m.get("model") or m.get("name")) else m
        for m in models_raw if isinstance(m, (dict, str))
    ]
    return web.json_response([m for m in models if isinstance(m, str)])


async def _save_diagram_handler(request):
    if request.method != "POST":
        return _json_err("Method not allowed", 405)
    try:
        data = await request.post()
    except Exception as e:
        return _json_err(str(e))
    file_field = data.get("file") or data.get("image")
    if not file_field or (not hasattr(file_field, "file") and not hasattr(file_field, "read")):
        return _json_err("No file in request (use field 'file' or 'image')")
    try:
        body, filename, content_type = _read_uploaded_file(file_field)
    except Exception as e:
        return _json_err(f"Failed to read file: {e}")
    if not body:
        return _json_err("Empty file")
    ct = content_type.split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_MIME:
        return _json_err("Disallowed type. Use image/png, image/svg+xml, or image/jpeg")
    ext = _safe_ext(content_type, filename)
    safe_name = f"uml_saved_{int(time.time() * 1000)}.{ext}"[:MAX_FILENAME_LEN]
    filepath = os.path.join(_get_uml_output_dir(), safe_name)
    try:
        with open(filepath, "wb") as f:
            f.write(body)
    except OSError as e:
        return _json_err(str(e), 500)
    return web.json_response({"path": filepath, "filename": safe_name, "relative": os.path.join("uml", safe_name)})


async def _proxy_diagram_handler(request):
    """GET /comfyui-uml/proxy?url=<encoded_diagram_url>. Fetches the URL server-side and returns the body with Content-Type to avoid CORS."""
    if request.method != "GET":
        return _json_err("Method not allowed", 405)
    if httpx is None:
        return _json_err("Proxy requires httpx", 503)

    raw = (request.query.get("url") or "").strip()
    if not raw:
        return _json_err("Missing url query parameter")
    try:
        parsed = urlparse(raw)
    except Exception:
        return _json_err("Invalid url")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return _json_err("url must be http or https")
    if parsed.netloc.lower().split(":")[0] not in PROXY_ALLOWED_NETLOCS:
        return _json_err("Proxy only allows kroki.io", 403)

    try:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(raw)
            r.raise_for_status()
            ct = (r.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
            return web.Response(body=r.content, content_type=ct)
    except httpx.HTTPStatusError as e:
        return web.Response(status=e.response.status_code, text=e.response.text)
    except Exception as e:
        return _json_err(str(e), 502)


def register_routes():
    if PromptServer is None or web is None:
        return
    try:
        instance = getattr(PromptServer, "instance", None)
        if instance is None:
            return
        routes = getattr(instance, "routes", None)
        if routes is None:
            return
        routes.post("/comfyui-uml/save")(_save_diagram_handler)
        routes.post("/comfyui-uml/ollama/get_models")(_ollama_get_models_handler)
        routes.get("/comfyui-uml/proxy")(_proxy_diagram_handler)
    except Exception:
        pass
