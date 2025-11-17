import pytest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import os
import json
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from writer.feedback_loop import FeedbackLoop


class TestFeedbackLoop:
    """Test cases for FeedbackLoop"""

    def test_init(self):
        """Test FeedbackLoop initialization"""
        loop = FeedbackLoop(
            writer_guidelines="Writer guidelines",
            reviewer_guidelines="Reviewer guidelines",
            folder_path="/test/folder",
            llm_provider="gemini",
            embedding_provider="openai",
        )

        assert loop.writer_guidelines == "Writer guidelines"
        assert loop.reviewer_guidelines == "Reviewer guidelines"
        assert loop.folder_path == "/test/folder"
        assert loop.llm_provider == "gemini"
        assert loop.embedding_provider == "openai"

    @patch("writer.feedback_loop.get_llm")
    @patch("writer.feedback_loop.KnowledgeIndexer")
    @patch("writer.feedback_loop.KnowledgeRetriever")
    def test_ensure_indexed_when_needed(
        self, mock_retriever_cls, mock_indexer_cls, mock_get_llm
    ):
        """Test ensuring knowledge base is indexed when not already indexed"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_indexer = MagicMock()
        mock_indexer_cls.return_value = mock_indexer

        mock_retriever = MagicMock()
        mock_retriever.is_indexed.return_value = False  # Not indexed
        mock_retriever_cls.return_value = mock_retriever

        loop = FeedbackLoop("writer", "reviewer", "/test/folder")

        with patch("builtins.print") as mock_print:
            loop._ensure_indexed()

            # Should call indexer to index documents
            mock_indexer_cls.assert_called_once_with(
                "/test/folder", embedding_provider="gemini", embedding_model=None
            )
            mock_indexer.index_documents.assert_called_once()
            mock_print.assert_called_once_with(
                "Knowledge base not indexed. Indexing now..."
            )

    @patch("writer.feedback_loop.get_llm")
    @patch("writer.feedback_loop.KnowledgeRetriever")
    def test_ensure_indexed_when_already_indexed(
        self, mock_retriever_cls, mock_get_llm
    ):
        """Test ensuring knowledge base when already indexed"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_retriever = MagicMock()
        mock_retriever.is_indexed.return_value = True  # Already indexed
        mock_retriever_cls.return_value = mock_retriever

        loop = FeedbackLoop("writer", "reviewer", "/test/folder")

        loop._ensure_indexed()

        # Should not call indexer
        mock_retriever.retrieve.assert_not_called()

    @patch("writer.feedback_loop.get_llm")
    @patch("writer.feedback_loop.KnowledgeRetriever")
    def test_retrieve_references_with_folder(self, mock_retriever_cls, mock_get_llm):
        """Test retrieving references when folder is provided"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"filepath": "ref1.md", "content": "content1", "chunk_id": "1"}
        ]
        mock_retriever_cls.return_value = mock_retriever

        loop = FeedbackLoop("writer", "reviewer", "/test/folder")

        result = loop._retrieve_references("test idea")

        assert result == [
            {"filepath": "ref1.md", "content": "content1", "chunk_id": "1"}
        ]
        mock_retriever.retrieve.assert_called_once_with("test idea", top_k=5)

    @patch("writer.feedback_loop.get_llm")
    def test_retrieve_references_without_folder(self, mock_get_llm):
        """Test retrieving references when no folder is provided"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        loop = FeedbackLoop("writer", "reviewer", None)

        result = loop._retrieve_references("test idea")

        assert result == []

    def test_apply_patch_operations(self):
        """Test applying patch operations (currently returns draft unchanged)"""
        loop = FeedbackLoop("writer", "reviewer")

        draft = "Original draft"
        result = loop._apply_patch_operations(draft, [])

        assert result == draft

    @patch("writer.feedback_loop.get_llm")
    @patch("writer.writer_agent.WriterAgent")
    @patch("writer.reviewer_agent.ReviewerAgent")
    @patch.object(FeedbackLoop, "_ensure_indexed")
    @patch.object(FeedbackLoop, "_retrieve_references")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_loop_accept_on_score(
        self,
        mock_open_file,
        mock_exists,
        mock_retrieve_refs,
        mock_ensure_indexed,
        mock_reviewer_cls,
        mock_writer_cls,
        mock_get_llm,
    ):
        """Test full run loop that accepts on score"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Setup writer agent
        mock_writer = MagicMock()
        mock_writer.generate_initial_draft.return_value = "Initial draft"
        mock_writer_cls.return_value = mock_writer

        # Setup reviewer agent
        mock_reviewer = MagicMock()
        mock_review_data = {
            "accept": False,
            "score": 95,  # High score, should accept
            "major_rewrite": False,
            "issues": [],
            "suggestions": [],
            "changes": [],
            "clarifying_questions": [],
        }
        mock_reviewer.review_draft.return_value = mock_review_data
        mock_reviewer_cls.return_value = mock_reviewer

        # Setup file mocks
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "Partial content"
        mock_open_file.return_value.__enter__.return_value = mock_file

        loop = FeedbackLoop("writer", "reviewer", "/test/folder")

        with patch("builtins.print"):
            draft, metadata = loop.run_loop(
                "test idea", max_iters=3, accept_threshold=90, output_file="/output.md"
            )

        # Verify the loop completed correctly
        assert draft == "Initial draft"
        assert metadata["score"] == 95
        assert metadata["iterations"] == 1
        assert metadata["accepted"] is True

        # Verify file operations
        mock_open_file.assert_called()

    @patch("writer.feedback_loop.get_llm")
    @patch("writer.writer_agent.WriterAgent")
    @patch("writer.reviewer_agent.ReviewerAgent")
    @patch.object(FeedbackLoop, "_ensure_indexed")
    @patch.object(FeedbackLoop, "_retrieve_references")
    def test_run_loop_max_iterations_reached(
        self,
        mock_retrieve_refs,
        mock_ensure_indexed,
        mock_reviewer_cls,
        mock_writer_cls,
        mock_get_llm,
    ):
        """Test run loop when max iterations are reached"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Setup writer agent
        mock_writer = MagicMock()
        mock_writer.generate_initial_draft.return_value = "Initial draft"
        mock_writer.regenerate_full_draft.return_value = "Improved draft"
        mock_writer_cls.return_value = mock_writer

        # Setup reviewer agent (always returns low score)
        mock_reviewer = MagicMock()
        mock_review_data = {
            "accept": False,
            "score": 70,  # Low score
            "major_rewrite": True,
            "issues": ["Issue"],
            "suggestions": ["Suggestion"],
            "changes": [],
            "clarifying_questions": [],
        }
        mock_reviewer.review_draft.return_value = mock_review_data
        mock_reviewer_cls.return_value = mock_reviewer

        mock_retrieve_refs.return_value = []

        loop = FeedbackLoop("writer", "reviewer")

        with patch("builtins.print"):
            draft, metadata = loop.run_loop(
                "test idea", max_iters=2, accept_threshold=90
            )

        # Should have gone through 2 iterations and stopped
        assert metadata["iterations"] == 2
        assert metadata["accepted"] is False
        mock_writer.regenerate_full_draft.assert_called()
