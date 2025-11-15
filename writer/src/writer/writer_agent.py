"""
Writer agent for the documentation generator.
Creates initial drafts and applies patches for edits.
"""

from typing import Optional, Dict, List, Any
from pathlib import Path
import json

from common.llm import get_llm


class WriterAgent:
    """Agent responsible for generating and editing content."""

    def __init__(self, llm_provider: str = "gemini"):
        self.llm_provider = llm_provider
        self.llm = get_llm(llm_provider)

    def _read_partial_doc(self, partial_path: Optional[str]) -> str:
        """Read partial document content."""
        if not partial_path:
            return ""

        path = Path(partial_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            print(f"Warning: Partial document not found: {partial_path}")
            return ""

    def _format_references(self, references: List[Dict]) -> str:
        """Format retrieved references for the prompt."""
        if not references:
            return "No specific references available."

        formatted = "Relevant knowledge references:\n"
        for i, ref in enumerate(references[:5], 1):  # Limit to top 5
            formatted += f"{i}. From {ref['filepath']}:\n{ref['content'][:500]}...\n\n"
        return formatted

    def generate_initial_draft(
        self,
        idea: str,
        references: List[Dict],
        guidelines: str,
        partial_doc: Optional[str] = None,
    ) -> str:
        """Generate the initial document draft."""

        partial_content = self._read_partial_doc(partial_doc) if partial_doc else ""
        formatted_refs = self._format_references(references)

        prompt = f"""
You are a writer creating comprehensive content based on an idea.

WRITER GUIDELINES:
{guidelines}

TASK:
Create a complete document for the following idea.

IDEA: {idea}

{f"PARTIAL DOCUMENT (continue from this): {partial_content}" if partial_content else ""}

RELEVANT KNOWLEDGE BASE REFERENCES:
{formatted_refs}

Generate the complete document in markdown format, dont include ```markdown tags.:
"""

        response = self.llm.invoke(prompt)
        return response.content.strip()

    def answer_clarifying_question(
        self,
        question: str,
        idea: str,
        references: List[Dict],
        guidelines: str,
        current_draft: Optional[str] = None,
    ) -> str:
        """Automatically answer a clarifying question using the LLM."""

        formatted_refs = self._format_references(references)

        prompt = f"""
You are a writer answering a clarifying question to help improve a documentation draft.

WRITER GUIDELINES:
{guidelines}

ORIGINAL IDEA: {idea}

{f"CURRENT DRAFT: {current_draft}" if current_draft else ""}

RELEVANT KNOWLEDGE BASE REFERENCES:
{formatted_refs}

QUESTION: {question}

Provide a concise, helpful answer to this clarifying question. Focus on practical details that will help create better documentation. Keep the answer focused and actionable.
"""

        response = self.llm.invoke(prompt)
        return response.content.strip()

    def apply_patch(
        self,
        current_draft: str,
        patch_operations: List[Dict[str, Any]],
        idea: str,
        references: List[Dict],
        guidelines: str,
    ) -> str:
        """Apply patch operations to edit the draft."""

        formatted_refs = self._format_references(references)
        formatted_patches = json.dumps(patch_operations, indent=2)

        prompt = f"""
You are a writer applying targeted edits to a document.

WRITER GUIDELINES:
{guidelines}

ORIGINAL IDEA: {idea}

CURRENT DRAFT:
{current_draft}

RELEVANT REFERENCES:
{formatted_refs}

PATCH OPERATIONS TO APPLY:
{formatted_patches}

Supported patch operations:
- replace: Replace specific old text with new text
- insert_before: Insert content before a specific anchor text
- insert_after: Insert content after a specific anchor text
- append: Append content to a specific section
- add_section: Add a new section with heading and content

Apply all the patch operations above to edit the current draft.
Output only the complete modified document.
Do not include any explanations or comments about the changes.
"""

        response = self.llm.invoke(prompt)
        return response.content.strip()

    def regenerate_full_draft(
        self,
        idea: str,
        references: List[Dict],
        guidelines: str,
        partial_doc: Optional[str] = None,
        current_draft: Optional[str] = None,
        issues: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        clarifying_answers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Regenerate the full draft (for major rewrites)."""

        partial_content = self._read_partial_doc(partial_doc) if partial_doc else ""
        formatted_refs = self._format_references(references)

        feedback_text = ""
        if issues or suggestions or clarifying_answers:
            feedback_parts = []
            if issues:
                feedback_parts.append(
                    "ISSUES FOUND:\n" + "\n".join(f"- {issue}" for issue in issues)
                )
            if suggestions:
                feedback_parts.append(
                    "SUGGESTIONS:\n"
                    + "\n".join(f"- {suggestion}" for suggestion in suggestions)
                )
            if clarifying_answers:
                feedback_parts.append(
                    "CLARIFYING ANSWERS:\n"
                    + "\n".join(
                        f"- {question}: {answer}"
                        for question, answer in clarifying_answers.items()
                    )
                )
            feedback_text = "\n\nREVIEW FEEDBACK:\n" + "\n\n".join(feedback_parts)

        context = f"""
ORIGINAL IDEA: {idea}

{f"PARTIAL DOCUMENT: {partial_content}" if partial_content else ""}

{f"PREVIOUS DRAFT: {current_draft}" if current_draft else ""}{feedback_text}
"""

        prompt = f"""
You are a writer performing a major rewrite of a document.

WRITER GUIDELINES:
{guidelines}

{context}

RELEVANT KNOWLEDGE BASE REFERENCES:
{formatted_refs}

Generate the complete revised document:
"""

        response = self.llm.invoke(prompt)
        return response.content.strip()
