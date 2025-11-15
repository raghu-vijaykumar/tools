"""
Feedback loop orchestrator for the writer-reviewer cycle.
Manages the iterative process until acceptance or max iterations.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

from .indexer import KnowledgeIndexer, KnowledgeRetriever
from .writer_agent import WriterAgent
from .reviewer_agent import ReviewerAgent


class FeedbackLoop:
    """Orchestrates the writer-reviewer feedback loop."""

    def __init__(
        self,
        writer_guidelines: str,
        reviewer_guidelines: str,
        folder_path: Optional[str] = None,
        llm_provider: str = "gemini",
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.folder_path = folder_path
        self.llm_provider = llm_provider
        self.embedding_provider = (
            embedding_provider or llm_provider
        )  # Default to same as LLM
        self.embedding_model = embedding_model

        # Initialize components
        self.indexer = (
            KnowledgeIndexer(
                folder_path,
                embedding_provider=self.embedding_provider,
                embedding_model=self.embedding_model,
            )
            if folder_path
            else None
        )
        self.retriever = (
            KnowledgeRetriever(
                folder_path,
                embedding_provider=self.embedding_provider,
                embedding_model=self.embedding_model,
            )
            if folder_path
            else None
        )
        self.writer = WriterAgent(llm_provider)
        self.reviewer = ReviewerAgent(llm_provider)

        self.writer_guidelines = writer_guidelines
        self.reviewer_guidelines = reviewer_guidelines

    def _ensure_indexed(self):
        """Ensure the knowledge base is indexed."""
        if self.retriever and not self.retriever.is_indexed():
            print("Knowledge base not indexed. Indexing now...")
            self.indexer.index_documents()

    def _retrieve_references(self, idea: str) -> List[Dict]:
        """Retrieve relevant references for the idea."""
        if self.retriever:
            return self.retriever.retrieve(idea, top_k=5)
        else:
            return []

    def _apply_patch_operations(self, draft: str, changes: List[Dict]) -> str:
        """
        Apply patch operations to draft manually if needed.
        For now, let the writer agent handle it via LLM.
        """
        # This is handled by WriterAgent.apply_patch()
        # So we just return the draft as-is here
        return draft

    def run_loop(
        self,
        idea: str,
        partial_doc: Optional[str] = None,
        max_iters: int = 3,
        accept_threshold: int = 90,
    ) -> Tuple[str, Dict]:
        """
        Run the complete writer-reviewer loop.

        Returns:
            Tuple of (final_draft, metadata_dict)
        """

        print(f"Starting documentation generation for: {idea}")
        print(f"LLM Provider: {self.llm_provider}")
        print(f"Max iterations: {max_iters}")

        # Ensure knowledge base is indexed
        self._ensure_indexed()

        # Retrieve relevant references
        references = self._retrieve_references(idea)
        print(f"Retrieved {len(references)} relevant references")

        # Generate initial draft
        draft = self.writer.generate_initial_draft(
            idea=idea,
            references=references,
            guidelines=self.writer_guidelines,
            partial_doc=partial_doc,
        )

        iterations = []
        accepted = False
        cumulative_answers = {}  # Track all answered questions across iterations

        for iteration in range(max_iters):
            print(f"\n--- Iteration {iteration + 1} ---")

            # Review the current draft
            review = self.reviewer.review_draft(
                draft=draft,
                idea=idea,
                references=references,
                guidelines=self.reviewer_guidelines,
                previous_answers=cumulative_answers,
            )

            print(f"Review score: {review['score']}")
            print(f"Accept: {review['accept']}")
            print(f"Major rewrite needed: {review['major_rewrite']}")

            if review["issues"]:
                print(f"Issues found: {len(review['issues'])}")

            # Handle clarifying questions
            clarifying_answers = {}
            if review["clarifying_questions"]:
                print(
                    f"\n🤔 Clarifying questions have been asked to improve the document:"
                )
                sys.stdout.flush()
                for i, question in enumerate(review["clarifying_questions"], 1):
                    print(f"{i}. {question}")
                print()
                sys.stdout.flush()

                for question in review["clarifying_questions"]:
                    print(f"? {question}")
                    sys.stdout.flush()
                    try:
                        answer = input().strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n[Input ended, continuing without clarifying answers]")
                        answer = ""
                    clarifying_answers[question] = answer
                    # Accumulate answers across iterations
                    cumulative_answers[question] = answer

            iterations.append(
                {
                    "iteration": iteration + 1,
                    "score": review["score"],
                    "issues": review["issues"],
                    "suggestions": review["suggestions"],
                    "clarifying_questions": review["clarifying_questions"],
                    "clarifying_answers": (
                        clarifying_answers if clarifying_answers else None
                    ),
                }
            )

            # Check acceptance
            if review["accept"] or review["score"] >= accept_threshold:
                print("Draft accepted!")
                accepted = True
                break

            # Check if max iterations reached
            if iteration == max_iters - 1:
                print("Max iterations reached. Using final draft.")
                break

            # Apply feedback
            if review["major_rewrite"]:
                print("Performing major rewrite...")
                draft = self.writer.regenerate_full_draft(
                    idea=idea,
                    references=references,
                    guidelines=self.writer_guidelines,
                    partial_doc=partial_doc,
                    current_draft=draft,
                    issues=review["issues"],
                    suggestions=review["suggestions"],
                    clarifying_answers=clarifying_answers,
                )
            else:
                print("Applying patch edits...")
                # Apply patch changes if any
                if review["changes"]:
                    draft = self.writer.apply_patch(
                        current_draft=draft,
                        patch_operations=review["changes"],
                        idea=idea,
                        references=references,
                        guidelines=self.writer_guidelines,
                    )
                else:
                    # No specific patches, but score needs improvement
                    # Generate improved version based on feedback
                    draft = self.writer.regenerate_full_draft(
                        idea=idea,
                        references=references,
                        guidelines=self.writer_guidelines,
                        partial_doc=partial_doc,
                        current_draft=draft,
                        issues=review["issues"],
                        suggestions=review["suggestions"],
                        clarifying_answers=clarifying_answers,
                    )

        # Generate metadata
        metadata = {
            "llm": self.llm_provider,
            "score": review["score"] if "review" in locals() else 0,
            "iterations": len(iterations),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "references": [
                {"file": ref["filepath"], "chunk": ref["chunk_id"]}
                for ref in references
            ],
            "iteration_details": iterations,
            "accepted": accepted,
        }

        print(f"\nProcess completed in {len(iterations)} iterations")
        print(f"Final score: {metadata['score']}")
        print(f"Document length: {len(draft)} characters")

        return draft, metadata
