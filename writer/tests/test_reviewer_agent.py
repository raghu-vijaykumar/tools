import pytest
from unittest.mock import MagicMock, patch
import json
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from writer.reviewer_agent import ReviewerAgent


class TestReviewerAgent:
    """Test cases for ReviewerAgent"""

    @patch("common.llm.get_llm")
    def test_init(self, mock_get_llm):
        """Test ReviewerAgent initialization"""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        assert agent.llm_provider == "gemini"
        assert agent.llm == mock_llm
        mock_get_llm.assert_called_once_with("gemini")

    @patch("common.llm.get_llm")
    def test_review_draft_successful(self, mock_get_llm):
        """Test successful draft review"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        review_data = {
            "accept": True,
            "score": 95,
            "major_rewrite": False,
            "issues": ["Minor formatting issue"],
            "suggestions": ["Consider adding more examples"],
            "changes": [
                {
                    "operation": "replace",
                    "params": {"old_text": "old", "new_text": "new"},
                }
            ],
            "clarifying_questions": [],
        }
        mock_response.content = json.dumps(review_data)
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        draft = "Test draft content"
        idea = "Test idea"
        references = [
            {"filepath": "ref.md", "content": "Reference content", "chunk_id": "1"}
        ]
        guidelines = "Test guidelines"

        result = agent.review_draft(draft, idea, references, guidelines)

        assert result["accept"] is True
        assert result["score"] == 95
        assert result["major_rewrite"] is False
        assert "Minor formatting issue" in result["issues"]
        assert "Consider adding more examples" in result["suggestions"]
        assert len(result["changes"]) == 1
        mock_llm.invoke.assert_called_once()

    @patch("common.llm.get_llm")
    def test_review_draft_with_markdown_json_response(self, mock_get_llm):
        """Test draft review with JSON wrapped in markdown code blocks"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        review_data = {
            "accept": False,
            "score": 75,
            "major_rewrite": True,
            "issues": ["Major content issue"],
            "suggestions": [],
            "changes": [],
            "clarifying_questions": ["What is the scope?"],
        }
        mock_response.content = f"```json\n{json.dumps(review_data)}\n```"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        result = agent.review_draft("draft", "idea", [], "guidelines")

        assert result["accept"] is False
        assert result["score"] == 75
        assert result["major_rewrite"] is True

    @patch("common.llm.get_llm")
    def test_review_draft_json_parse_error(self, mock_get_llm):
        """Test draft review when LLM returns invalid JSON"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Invalid JSON response"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        result = agent.review_draft("draft", "idea", [], "guidelines")

        # Should return default review when JSON parsing fails
        assert result["accept"] is False
        assert result["score"] == 60
        assert result["major_rewrite"] is True
        assert "Failed to parse reviewer feedback" in result["issues"]

    @patch("common.llm.get_llm")
    def test_review_draft_missing_fields(self, mock_get_llm):
        """Test draft review when response is missing required fields"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        # Missing some required fields
        review_data = {
            "accept": True,
            "score": 85,
            # Missing major_rewrite, issues, etc.
        }
        mock_response.content = json.dumps(review_data)
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        result = agent.review_draft("draft", "idea", [], "guidelines")

        # Should populate missing fields with defaults
        assert result["accept"] is True
        assert result["score"] == 85
        assert result["major_rewrite"] is False  # default
        assert result["issues"] == []  # default

    @patch("common.llm.get_llm")
    def test_review_draft_with_previous_answers_filters_questions(self, mock_get_llm):
        """Test draft review filters out previously answered clarifying questions"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        review_data = {
            "accept": False,
            "score": 70,
            "major_rewrite": False,
            "issues": [],
            "suggestions": [],
            "changes": [],
            "clarifying_questions": [
                "What is the scope?",
                "How does this work?",  # This one is new
                "What are the benefits?",  # This one should be filtered
            ],
        }
        mock_response.content = json.dumps(review_data)
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        previous_answers = {
            "What are the key benefits?": "Many benefits",
            "Scope details?": "Scope is limited",
        }

        result = agent.review_draft("draft", "idea", [], "guidelines", previous_answers)

        # Should keep only non-similar questions
        assert "How does this work?" in result["clarifying_questions"]
        assert len(result["clarifying_questions"]) >= 1

    @patch("common.llm.get_llm")
    def test_review_draft_score_clamping(self, mock_get_llm):
        """Test that review scores are clamped to 0-100 range"""
        mock_llm = MagicMock()
        mock_response = MagicMock()

        # Test score > 100
        review_data = {
            "accept": True,
            "score": 150,
            "major_rewrite": False,
            "issues": [],
            "suggestions": [],
            "changes": [],
            "clarifying_questions": [],
        }
        mock_response.content = json.dumps(review_data)
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        agent = ReviewerAgent("gemini")

        result = agent.review_draft("draft", "idea", [], "guidelines")

        assert result["score"] == 100  # Clamped

        # Test negative score
        review_data["score"] = -10
        mock_response.content = json.dumps(review_data)

        result = agent.review_draft("draft", "idea", [], "guidelines")

        assert result["score"] == 0  # Clamped

    def test_are_questions_similar_exact_match(self):
        """Test question similarity detection - exact match"""
        agent = ReviewerAgent("gemini")

        assert agent._are_questions_similar("What is the scope?", "What is the scope?")
        assert not agent._are_questions_similar(
            "What is the scope?", "How does it work?"
        )

    def test_are_questions_similar_normalized(self):
        """Test question similarity detection - normalized match"""
        agent = ReviewerAgent("gemini")

        assert agent._are_questions_similar("What is the scope?", "what is the scope?")
        assert agent._are_questions_similar("What is the scope!", "what is the scope")

    def test_are_questions_similar_contained(self):
        """Test question similarity detection - one contained in other"""
        agent = ReviewerAgent("gemini")

        assert agent._are_questions_similar(
            "What is the project scope?", "What is the scope?"
        )
        assert agent._are_questions_similar(
            "What is the scope?", "What is the detailed project scope and timeline?"
        )
