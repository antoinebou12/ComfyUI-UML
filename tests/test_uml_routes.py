"""
Tests for ComfyUI-UML backend routes and URL helpers.
No external HTTP calls; mocks used where needed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nodes.uml_routes import _safe_ext, _proxy_diagram_handler
from nodes.uml_viewer_url import _normalize_url


# --- _safe_ext ---------------------------------------------------------------


def test_safe_ext_mime_png():
    assert _safe_ext("image/png", None) == "png"


def test_safe_ext_mime_svg():
    assert _safe_ext("image/svg+xml", None) == "svg"


def test_safe_ext_mime_jpeg():
    assert _safe_ext("image/jpeg", None) == "jpeg"


def test_safe_ext_mime_unknown_fallback_filename():
    assert _safe_ext("application/octet-stream", "diagram.png") == "png"
    assert _safe_ext("application/octet-stream", "out.svg") == "svg"


def test_safe_ext_mime_none_filename_jpg_normalized_to_png():
    assert _safe_ext(None, "x.jpg") == "png"


def test_safe_ext_mime_none_filename_jpeg():
    assert _safe_ext(None, "x.jpeg") == "jpeg"


def test_safe_ext_no_mime_no_filename_returns_png():
    assert _safe_ext(None, None) == "png"


def test_safe_ext_filename_extension_case_insensitive():
    assert _safe_ext(None, "x.PNG") == "png"
    assert _safe_ext(None, "x.SVG") == "svg"


# --- _proxy_diagram_handler (guard logic only, no real HTTP) -----------------


def _make_web_mock():
    """Fake aiohttp.web so handler can return response-like objects when web is None (e.g. outside ComfyUI)."""
    web = MagicMock()
    def json_response(body, status=200):
        return MagicMock(status=status, body=body)
    def response(body=b"", content_type="application/octet-stream"):
        return MagicMock(status=200, body=body, content_type=content_type)
    web.json_response = json_response
    web.Response = response
    return web


@pytest.mark.asyncio
async def test_proxy_disallowed_netloc_returns_403():
    request = MagicMock()
    request.method = "GET"
    request.query.get = lambda k, default=None: "http://evil.com/diagram" if k == "url" else default

    with patch("nodes.uml_routes.httpx", MagicMock()), patch("nodes.uml_routes.web", _make_web_mock()):
        resp = await _proxy_diagram_handler(request)
    assert resp.status == 403
    body = getattr(resp, "body", b"")
    if isinstance(body, dict):
        body = str(body).encode()
    elif isinstance(body, str):
        body = body.encode()
    assert b"kroki" in body


@pytest.mark.asyncio
async def test_proxy_allowed_netloc_does_not_return_403():
    """With allowed netloc, handler proceeds; we mock httpx so no real request is made."""
    request = MagicMock()
    request.method = "GET"
    request.query.get = lambda k, default=None: "https://kroki.io/seqdiag/svg/abc" if k == "url" else default

    async def fake_get(url):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.content = b"<svg/>"
        r.headers = {"content-type": "image/svg+xml"}
        return r

    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=fake_get)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    web_mock = _make_web_mock()
    with patch("nodes.uml_routes.httpx") as m_httpx, patch("nodes.uml_routes.web", web_mock):
        m_httpx.AsyncClient = MagicMock(return_value=fake_client)
        resp = await _proxy_diagram_handler(request)
    assert resp.status != 403
    assert resp.status == 200


# --- _normalize_url (uml_viewer_url) ------------------------------------------


def test_normalize_url_string():
    assert _normalize_url("  https://kroki.io/foo  ") == "https://kroki.io/foo"


def test_normalize_url_none():
    assert _normalize_url(None) == ""


def test_normalize_url_list_takes_first():
    assert _normalize_url(["https://first", "https://second"]) == "https://first"


def test_normalize_url_empty_list():
    # Empty list falls through to str(value).strip() -> "[]"
    assert _normalize_url([]) == "[]"


def test_normalize_url_object_with_text_attr():
    class Obj:
        text = "  https://example.com  "
    assert _normalize_url(Obj()) == "https://example.com"


def test_normalize_url_object_with_content_attr():
    class Obj:
        content = "https://content.com"
    assert _normalize_url(Obj()) == "https://content.com"


def test_normalize_url_object_fallback_str():
    class Obj:
        def __str__(self):
            return "  fallback  "
    assert _normalize_url(Obj()) == "fallback"
