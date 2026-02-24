"""
Register ComfyUI-UML API route: POST /comfyui-uml/save to save diagram from viewer to output/uml/.
"""
import os
import time

try:
    from server import PromptServer
    from aiohttp import web
except ImportError:
    PromptServer = None
    web = None

ALLOWED_MIME = frozenset({"image/png", "image/svg+xml", "image/jpeg"})
MIME_TO_EXT = {"image/png": "png", "image/svg+xml": "svg", "image/jpeg": "jpeg"}
MAX_FILENAME_LEN = 200


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


async def _save_diagram_handler(request):
    if request.method != "POST":
        return web.json_response({"error": "Method not allowed"}, status=405)
    try:
        data = await request.post()
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)
    file_field = data.get("file") or data.get("image")
    if not file_field or not hasattr(file_field, "file") and not hasattr(file_field, "read"):
        return web.json_response({"error": "No file in request (use field 'file' or 'image')"}, status=400)
    try:
        if hasattr(file_field, "file"):
            body = file_field.file.read()
            filename = getattr(file_field, "filename", None) or ""
            content_type = getattr(file_field, "content_type", None) or ""
        else:
            body = file_field.read() if callable(getattr(file_field, "read", None)) else bytes(file_field)
            filename = getattr(file_field, "filename", "") or ""
            content_type = getattr(file_field, "content_type", "") or ""
    except Exception as e:
        return web.json_response({"error": f"Failed to read file: {e}"}, status=400)
    if not body:
        return web.json_response({"error": "Empty file"}, status=400)
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_MIME:
        return web.json_response({"error": f"Disallowed type: {content_type}. Use image/png, image/svg+xml, or image/jpeg"}, status=400)
    ext = _safe_ext(content_type, filename)
    safe_name = f"uml_saved_{int(time.time() * 1000)}.{ext}"
    if len(safe_name) > MAX_FILENAME_LEN:
        safe_name = safe_name[:MAX_FILENAME_LEN]
    out_dir = _get_uml_output_dir()
    filepath = os.path.join(out_dir, safe_name)
    try:
        with open(filepath, "wb") as f:
            f.write(body)
    except OSError as e:
        return web.json_response({"error": str(e)}, status=500)
    rel_path = os.path.join("uml", safe_name)
    return web.json_response({"path": filepath, "filename": safe_name, "relative": rel_path})


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
    except Exception:
        pass
