import pytest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.llm import get_llm, summarize_article


class TestLLMFunctions:
    """Test cases for LLM-related functions"""

    @patch("common.llm.llm_client")
    def test_get_llm_gemini(self, mock_client):
        """Test getting Gemini LLM"""
        mock_llm = MagicMock()
        mock_client.get_llm.return_value = mock_llm

        result = get_llm("gemini")

        mock_client.get_llm.assert_called_once_with("gemini")
        assert result == mock_llm

    @patch("common.llm.llm_client")
    def test_get_llm_openai(self, mock_client):
        """Test getting OpenAI LLM"""
        mock_llm = MagicMock()
        mock_client.get_llm.return_value = mock_llm

        result = get_llm("openai")

        mock_client.get_llm.assert_called_once_with("openai")
        assert result == mock_llm

    @patch("common.llm.last_llm_call", 0)
    @patch("time.time")
    @patch("time.sleep")
    @patch("common.llm.get_llm")
    def test_summarize_article_success(self, mock_get_llm, mock_sleep, mock_time):
        """Test successful article summarization"""
        mock_time.return_value = 10.0  # Current time
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary content"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        article = {"title": "Test Article", "summary": "Article content"}

        result = summarize_article(article, "gemini")

        assert result == "Summary content"
        mock_get_llm.assert_called_once_with("gemini")
        mock_llm.invoke.assert_called_once()

        # Check that sleep was called (rate limiting)
        mock_sleep.assert_called_once()

    @patch("common.llm.last_llm_call", 10.0)
    @patch("time.time")
    @patch("time.sleep")
    @patch("common.llm.get_llm")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="File content")
    def test_summarize_article_from_file(
        self, mock_file_open, mock_exists, mock_get_llm, mock_sleep, mock_time
    ):
        """Test article summarization with content from file"""
        mock_time.return_value = 10.1  # Just over the wait time
        mock_exists.return_value = True
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "File summary"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        article = {"title": "Test Article", "content_path": "/path/to/content.txt"}

        result = summarize_article(article, "openai")

        assert result == "File summary"
        mock_file_open.assert_called_once_with(
            "/path/to/content.txt", "r", encoding="utf-8"
        )
        mock_sleep.assert_not_called()  # No sleep needed
