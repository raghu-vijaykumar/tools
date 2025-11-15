"""
Reviewer agent for the documentation generator.
Reviews drafts and provides structured feedback with scores and patch operations.
"""

from typing import Dict, List, Optional
from pathlib import Path
import json

from common.llm import get_llm


class ReviewerAgent:
    """Agent responsible for reviewing and scoring drafts."""

    def __init__(self, llm_provider: str = "gemini"):
        self.llm_provider = llm_provider
        self.llm = get_llm(llm_provider)

    def review_draft(
        self,
        draft: str,
        idea: str,
        references: List[Dict],
        guidelines: str,
        previous_answers: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """
        Review a draft and return structured feedback.

        Returns:
            Dict with keys: accept, score, major_rewrite, issues, suggestions, changes, clarifying_questions
        """

        # Format references for context
        formatted_refs = ""
        if references:
            formatted_refs = "\nRelevant knowledge references used in drafting:\n"
            for i, ref in enumerate(references[:3], 1):
                formatted_refs += f"{i}. {ref['filepath']}: {ref['content'][:300]}...\n"

        # Format previous clarifying answers
        formatted_answers = ""
        if previous_answers:
            formatted_answers = "\nPREVIOUSLY ANSWERED CLARIFYING QUESTIONS:\n"
            for question, answer in previous_answers.items():
                formatted_answers += f"Q: {question}\nA: {answer}\n\n"

        prompt = f"""
You are a reviewer evaluating a draft document.

REVIEWER GUIDELINES:
{guidelines}

ORIGINAL IDEA: {idea}

DOCUMENT DRAFT TO REVIEW:
{draft}

{formatted_refs}{formatted_answers}

Your task is to provide a comprehensive review in JSON format only.

IMPORTANT NOTES FOR REVIEW:
- If clarifying questions have been previously answered (shown above), assume those answers have been incorporated into the document. Focus on NEW issues or areas not covered by previous answers.
- When calculating the score, consider that previous clarifying questions indicate missing information that has now been addressed through assumptions and improvements.
- Look for actual improvements and completeness rather than assuming the document is missing critical information (since previous answers provide that context).

IMPORTANT: When generating clarifying_questions, DO NOT ask any questions that have already been answered above.
If you need clarification but a similar question has already been answered, try to phrase new questions differently or avoid asking if the information is already available.

Calculate an overall score (0-100) based on the provided guidelines and general quality criteria.

RESPONSE FORMAT - Return only valid JSON:
{{
  "accept": true/false,
  "score": 0-100,
  "major_rewrite": true/false,
  "issues": ["Array of specific problems found with section/line references"],
  "suggestions": ["Array of actionable improvement recommendations"],
  "changes": [
     {{"operation": "replace/insert_before/insert_after/append/add_section", "params": {{...}} }}
   ],
  "clarifying_questions": ["Questions for writer to address ambiguities"]
}}

RULES:
- accept=true only if score >= 90 and no major issues
- major_rewrite=true if score < 70 or requires complete restructuring
- For patch operations, use these formats:
  {{"operation": "replace", "params": {{"old_text": "exact text to replace", "new_text": "replacement text"}} }}
  {{"operation": "insert_before", "params": {{"anchor": "text to find", "content": "text to insert"}} }}
  {{"operation": "insert_after", "params": {{"anchor": "text to find", "content": "text to insert"}} }}
  {{"operation": "append", "params": {{"section": "# Section Name", "content": "additional content"}} }}
  {{"operation": "add_section", "params": {{"heading": "## New Section", "content": "section content"}} }}
- Prioritize patch operations for minor fixes when score >= 70
- Be specific and actionable in feedback
"""

        response = self.llm.invoke(prompt)

        try:
            # Strip markdown code blocks if present
            content = response.content.strip()
            if content.startswith("```json") and content.endswith("```"):
                content = content[7:-3].strip()

            result = json.loads(content)
            # Validate required fields
            required_fields = [
                "accept",
                "score",
                "major_rewrite",
                "issues",
                "suggestions",
                "changes",
                "clarifying_questions",
            ]
            for field in required_fields:
                if field not in result:
                    result[field] = (
                        []
                        if field
                        in ["issues", "suggestions", "changes", "clarifying_questions"]
                        else (
                            False
                            if field == "accept"
                            else 50 if field == "score" else False
                        )
                    )

            # Ensure score is in valid range
            result["score"] = max(0, min(100, result["score"]))

            # Filter out clarifying questions that have already been answered
            if previous_answers and result["clarifying_questions"]:
                print(
                    f"\n[DEBUG] Filtering {len(result['clarifying_questions'])} questions against {len(previous_answers)} previous answers..."
                )
                filtered_questions = []
                filtered_count = 0
                for question in result["clarifying_questions"]:
                    # Only include questions that haven't been asked before
                    is_already_answered = any(
                        self._are_questions_similar(question, answered_question)
                        for answered_question in previous_answers.keys()
                    )
                    if not is_already_answered:
                        filtered_questions.append(question)
                    else:
                        filtered_count += 1
                        print(
                            f"[DEBUG] FILTERED OUT similar question: {question[:60]}..."
                        )
                result["clarifying_questions"] = filtered_questions
                print(
                    f"[DEBUG] Kept {len(filtered_questions)} questions, filtered {filtered_count}"
                )

            return result

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse reviewer response as JSON: {e}")
            print("Response:", response.content)
            # Return default review
            return {
                "accept": False,
                "score": 60,
                "major_rewrite": True,
                "issues": ["Failed to parse reviewer feedback"],
                "suggestions": ["Please regenerate the review"],
                "changes": [],
                "clarifying_questions": [],
            }

    def _are_questions_similar(self, question1: str, question2: str) -> bool:
        """
        Check if two questions are similar enough to be considered the same.

        Uses simple heuristics: exact match, normalized match (lowercase, remove punctuation),
        or if one is contained within the other (for longer/shorter versions).
        """
        import re

        # Normalize questions: lowercase, remove punctuation except slashes, normalize whitespace
        def normalize(q):
            q = q.lower()
            q = re.sub(
                r"[^\w\s/]", "", q
            )  # Remove punctuation but keep word chars, spaces, slashes
            q = re.sub(r"\s+", " ", q)  # Normalize whitespace
            return q.strip()

        q1_norm = normalize(question1)
        q2_norm = normalize(question2)

        # Exact match
        if q1_norm == q2_norm:
            return True

        # Check if one is contained in the other (handle minor rephrasing)
        # Only if both are reasonably long (>10 chars)
        if len(q1_norm) > 10 and len(q2_norm) > 10:
            if q1_norm in q2_norm or q2_norm in q1_norm:
                return True

        return False
