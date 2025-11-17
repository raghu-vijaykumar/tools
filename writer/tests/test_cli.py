import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from writer.cli import app


class TestCLI:
    """Test cases for CLI functionality"""

    def test_app_exists(self):
        """Test that the CLI app exists"""
        assert app is not None

    @patch("writer.cli.setup_logging")
    @patch("writer.cli.FeedbackLoop")
    @patch("writer.cli.Path")
    @patch("builtins.open")
    def test_run_command_basic(
        self, mock_open, mock_path, mock_feedback_loop_cls, mock_setup_logging
    ):
        """Test the run command with basic parameters"""
        # Setup mocks
        mock_loop = MagicMock()
        mock_loop.run_loop.return_value = (
            "Generated content",
            {"score": 95, "iterations": 1},
        )
        mock_feedback_loop_cls.return_value = mock_loop

        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_dir.return_value = True
        mock_path.return_value.parent.mkdir = MagicMock()

        # Import typer testing utilities
        from typer.testing import CliRunner

        runner = CliRunner()

        # Run the command
        result = runner.invoke(
            app,
            [
                "run",
                "--idea",
                "Test idea",
                "--writer-guidelines",
                "test_writer.md",
                "--reviewer-guidelines",
                "test_reviewer.md",
                "--output",
                "output.md",
            ],
        )

        # Should succeed (exit code 0)
        assert result.exit_code == 0
        mock_feedback_loop_cls.assert_called_once()
        mock_loop.run_loop.assert_called_once()

    @patch("writer.cli.setup_logging")
    @patch("writer.cli.FeedbackLoop")
    @patch("writer.cli.KnowledgeIndexer")
    def test_index_command(
        self, mock_indexer_cls, mock_feedback_loop_cls, mock_setup_logging
    ):
        """Test the index command"""
        mock_indexer = MagicMock()
        mock_indexer_cls.return_value = mock_indexer

        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(app, ["index", "--folder", "/test/folder"])

        assert result.exit_code == 0
        mock_indexer_cls.assert_called_once_with(
            "/test/folder", embedding_provider="openai", embedding_model=None
        )
        mock_indexer.index_documents.assert_called_once()
