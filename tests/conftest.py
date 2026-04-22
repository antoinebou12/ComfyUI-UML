"""Pytest configuration: ensure project root is on sys.path for node imports."""
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Importing `nodes.uml_routes` must not execute `nodes/__init__.py` (that pulls torch/numpy).
# Register a lightweight namespace-style package first so submodule imports stay headless.
if "nodes" not in sys.modules:
    _nodes_pkg = types.ModuleType("nodes")
    _nodes_pkg.__path__ = [str(_root / "nodes")]
    sys.modules["nodes"] = _nodes_pkg


@pytest.fixture
def fake_aiohttp_web():
    """Fake aiohttp.web so route handlers can return response-like objects when web is None."""
    web = MagicMock()

    def json_response(body, status=200):
        return MagicMock(status=status, body=body)

    def response(body=b"", content_type="application/octet-stream"):
        return MagicMock(status=200, body=body, content_type=content_type)

    web.json_response = json_response
    web.Response = response
    return web


@pytest.fixture
def mock_httpx_async_client_for_kroki_proxy():
    """AsyncClient mock: successful GET returning SVG bytes (no real HTTP)."""
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
    return fake_client
