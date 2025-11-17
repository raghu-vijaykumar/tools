import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from writer.writer_agent import WriterAgent


@pytest.fixture
def mock_llm():
    """Create a mock LLM with invoke method"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Mock response content"
    mock_llm.invoke.return_value = mock_response
    return mock_llm


@pytest.fixture
def agent(mock_llm):
    """Create a WriterAgent with mocked LLM"""
    with patch("writer.writer_agent.get_llm", return_value=mock_llm):
        agent = WriterAgent("gemini")
        yield agent


class TestWriterAgent:
    """Test cases for WriterAgent"""

    @patch("writer.writer_agent.get_llm")
    def test_init(self, mock_get_llm):
        """Test WriterAgent initialization"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = WriterAgent("gemini")

        assert agent.llm_provider == "gemini"
        assert agent.llm == mock_llm
        mock_get_llm.assert_called_once_with("gemini")

    def test_generate_initial_draft(self, agent, mock_llm):
        """Test initial draft generation"""
        # Configure the mock response for this test
        mock_llm.invoke.return_value.content = "Generated draft content"

        idea = "Test idea"
        references = [
            {"filepath": "test.md", "content": "Reference content", "chunk_id": "1"}
        ]
        guidelines = "Test guidelines"

        result = agent.generate_initial_draft(idea, references, guidelines)

        assert result == "Generated draft content"
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert idea in call_args
        assert guidelines in call_args
        assert "Reference content" in call_args

    @patch("writer.writer_agent.get_llm")
    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_generate_initial_draft_with_partial_doc(
        self, mock_exists, mock_open, mock_get_llm
    ):
        """Test initial draft generation with partial document"""
        # Setup mocks
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Generated draft content"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "Partial content"
        mock_open.return_value.__enter__.return_value = mock_file

        agent = WriterAgent("gemini")

        idea = "Test idea"
        references = []
        guidelines = "Test guidelines"
        partial_doc = "/path/to/partial.md"

        result = agent.generate_initial_draft(idea, references, guidelines, partial_doc)

        assert result == "Generated draft content"
        mock_exists.assert_called_once()
        mock_open.assert_called_once()
        mock_llm.invoke.assert_called_once()

    def test_format_references_empty(self):
        """Test formatting empty references"""
        agent = WriterAgent("gemini")

        result = agent._format_references([])

        assert result == "No specific references available."

    def test_format_references_with_content(self):
        """Test formatting references with content"""
        agent = WriterAgent("gemini")

        references = [
            {"filepath": "test1.md", "content": "Content 1", "chunk_id": "1"},
            {"filepath": "test2.md", "content": "Content 2", "chunk_id": "2"},
        ]

        result = agent._format_references(references)

        assert "test1.md" in result
        assert "Content 1..." in result
        assert "test2.md" in result
        assert "Content 2..." in result

    @patch("writer.writer_agent.get_llm")
    def test_answer_clarifying_question(self, mock_get_llm):
        """Test answering clarifying questions"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Clarified answer"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = WriterAgent("gemini")

        question = "What is the scope?"
        idea = "Test idea"
        references = []
        guidelines = "Test guidelines"
        current_draft = "Current draft content"

        result = agent.answer_clarifying_question(
            question, idea, references, guidelines, current_draft
        )

        assert result == "Clarified answer"
        mock_llm.invoke.assert_called_once()

    @patch("writer.writer_agent.get_llm")
    def test_apply_patch(self, mock_get_llm):
        """Test applying patches to draft"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Patched content"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = WriterAgent("gemini")

        current_draft = "Original content"
        patch_operations = [{"replace": "old", "with": "new"}]
        idea = "Test idea"
        references = []
        guidelines = "Test guidelines"

        result = agent.apply_patch(
            current_draft, patch_operations, idea, references, guidelines
        )

        assert result == "Patched content"
        mock_llm.invoke.assert_called_once()

    @patch("writer.writer_agent.get_llm")
    def test_regenerate_full_draft(self, mock_get_llm):
        """Test full draft regeneration"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Regenerated content"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = WriterAgent("gemini")

        idea = "Test idea"
        references = []
        guidelines = "Test guidelines"
        issues = ["Issue 1", "Issue 2"]
        suggestions = ["Suggestion 1"]
        clarifying_answers = {"Question": "Answer"}

        result = agent.regenerate_full_draft(
            idea,
            references,
            guidelines,
            issues=issues,
            suggestions=suggestions,
            clarifying_answers=clarifying_answers,
        )

        assert result == "Regenerated content"
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert "Issue 1" in call_args
        assert "Suggestion 1" in call_args
        assert "Question: Answer" in call_args
