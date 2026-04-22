"""Tests for use_mock_llm() env logic (no LLM HTTP)."""

import pytest

from nodes.uml_llm_shared import use_mock_llm


@pytest.fixture(autouse=True)
def clear_llm_mock_env(monkeypatch):
    for key in ("COMFY_UI_UML_MOCK_LLM", "GITHUB_ACTIONS"):
        monkeypatch.delenv(key, raising=False)
    yield


def test_explicit_one(monkeypatch):
    monkeypatch.setenv("COMFY_UI_UML_MOCK_LLM", "1")
    assert use_mock_llm() is True


def test_explicit_zero_disables_even_in_actions(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("COMFY_UI_UML_MOCK_LLM", "0")
    assert use_mock_llm() is False


def test_github_actions_defaults_mock(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert use_mock_llm() is True


def test_local_default_no_mock(monkeypatch):
    assert use_mock_llm() is False
