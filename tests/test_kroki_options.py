"""Tests for Kroki diagram_options JSON parsing (no ComfyUI / torch)."""

import pytest

from nodes.kroki_client import kroki_options_from_widgets, parse_diagram_options_json


def test_parse_empty():
    assert parse_diagram_options_json("") == {}
    assert parse_diagram_options_json("   ") == {}
    assert parse_diagram_options_json(None) == {}


def test_parse_object():
    assert parse_diagram_options_json('{"scale": 2}') == {"scale": 2}


def test_parse_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_diagram_options_json("{not json")


def test_parse_not_object():
    with pytest.raises(ValueError, match="JSON object"):
        parse_diagram_options_json("[1,2]")


def test_kroki_options_from_widgets_theme_merge():
    opts, theme = kroki_options_from_widgets('{"scale": 1}', "forest")
    assert opts == {"scale": 1, "theme": "forest"}
    assert theme == "forest"


def test_kroki_options_from_widgets_empty():
    opts, theme = kroki_options_from_widgets("", "")
    assert opts is None
    assert theme is None
