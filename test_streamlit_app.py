# -*- coding: utf-8 -*-
"""Tests for streamlit_app.py helpers and UI logic."""

import importlib
import json
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Provide a lightweight Streamlit stub so the module can be imported without
# a running Streamlit server.  Only the attributes actually used at import
# time need to be stubbed.
# ---------------------------------------------------------------------------

_st_stub = types.ModuleType("streamlit")

# Simple no-ops / identity stubs for every st.* function used at module level
for _fn_name in (
    "set_page_config", "title", "markdown", "header", "subheader",
    "selectbox", "text_input", "text_area", "divider", "info",
    "button", "spinner", "success", "error", "tabs", "columns",
    "metric", "code", "json", "download_button", "caption",
):
    setattr(_st_stub, _fn_name, MagicMock())

# st.sidebar must behave as a context manager
_sidebar_mock = MagicMock()
_sidebar_mock.__enter__ = MagicMock(return_value=_sidebar_mock)
_sidebar_mock.__exit__ = MagicMock(return_value=False)
_sidebar_mock.header = MagicMock()
_sidebar_mock.subheader = MagicMock()
_sidebar_mock.selectbox = MagicMock(return_value="Spring Boot")
_sidebar_mock.text_input = MagicMock(return_value="")
_sidebar_mock.text_area = MagicMock(return_value="")
_sidebar_mock.divider = MagicMock()
_sidebar_mock.info = MagicMock()
_st_stub.sidebar = _sidebar_mock

# Patch before importing the module under test
sys.modules.setdefault("streamlit", _st_stub)

# Now we can safely import the helpers
from streamlit_app import _build_category_map, _init_client  # noqa: E402


# ──────────────────────────────────────────────────────────────────
# Tests for _build_category_map
# ──────────────────────────────────────────────────────────────────

class TestBuildCategoryMap:
    """Verify _build_category_map mirrors seed_data.TAXONOMY correctly."""

    def test_returns_dict(self):
        result = _build_category_map()
        assert isinstance(result, dict)

    def test_contains_all_categories(self):
        from seed_data import TAXONOMY
        result = _build_category_map()
        for cat in TAXONOMY:
            assert cat["name"] in result

    def test_subcategories_are_dicts(self):
        result = _build_category_map()
        for _cat_name, sub_map in result.items():
            assert isinstance(sub_map, dict)

    def test_tags_are_lists(self):
        result = _build_category_map()
        for _cat_name, sub_map in result.items():
            for _sub_name, tags in sub_map.items():
                assert isinstance(tags, list)

    def test_spring_boot_has_subcategories(self):
        result = _build_category_map()
        assert "Spring Boot" in result
        assert len(result["Spring Boot"]) > 0

    def test_subcategory_contains_tags(self):
        result = _build_category_map()
        # Pick the first subcategory of the first category
        first_cat = list(result.keys())[0]
        first_sub = list(result[first_cat].keys())[0]
        tags = result[first_cat][first_sub]
        assert len(tags) > 0


# ──────────────────────────────────────────────────────────────────
# Tests for _init_client
# ──────────────────────────────────────────────────────────────────

class TestInitClient:
    """Verify AI client initialization for each provider."""

    @patch("streamlit_app._is_ollama_provider", return_value=True)
    @patch("streamlit_app.OpenAI")
    def test_ollama_provider(self, mock_openai_cls, _mock_ollama):
        mock_openai_cls.return_value = MagicMock()
        client = _init_client()
        mock_openai_cls.assert_called_once()
        assert client is not None

    @patch("streamlit_app._is_ollama_provider", return_value=False)
    @patch("streamlit_app._is_gemini_model", return_value=True)
    def test_gemini_provider_returns_none(self, _mock_gemini, _mock_ollama):
        client = _init_client()
        assert client is None

    @patch("streamlit_app._is_ollama_provider", return_value=False)
    @patch("streamlit_app._is_gemini_model", return_value=False)
    @patch("streamlit_app.OPENAIAPIKEY", "sk-test-key")
    @patch("streamlit_app.OpenAI")
    def test_openai_provider(self, mock_openai_cls, _mock_gemini, _mock_ollama):
        mock_openai_cls.return_value = MagicMock()
        client = _init_client()
        mock_openai_cls.assert_called_once()
        assert client is not None

    @patch("streamlit_app._is_ollama_provider", return_value=False)
    @patch("streamlit_app._is_gemini_model", return_value=False)
    @patch("streamlit_app.OPENAIAPIKEY", "")
    def test_no_api_key_returns_none(self, _mock_gemini, _mock_ollama):
        client = _init_client()
        assert client is None
