"""
CLI for the AI documentation generator.
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import json

from .feedback_loop import FeedbackLoop
from common.logging import setup_logging

app = typer.Typer()
console = Console()


@app.callback()
def callback():
    """
    AI documentation generator with writer-reviewer loop.
    """
    pass


@app.command()
def run(
    idea: str = typer.Option(..., help="The idea to document"),
    references_folder: str = typer.Option(
        None, help="Optional single-folder knowledge base path"
    ),
    llm: str = typer.Option("gemini", help="LLM provider (openai or gemini)"),
    embedding_provider: str = typer.Option(
        None,
        help="Embedding provider (openai, gemini, huggingface, sentence-transformers). Defaults to same as --llm",
    ),
    embedding_model: str = typer.Option(
        None, help="Specific embedding model name (optional, uses provider defaults)"
    ),
    writer_guidelines: str = typer.Option(..., help="Path to writer guidelines file"),
    reviewer_guidelines: str = typer.Option(
        ..., help="Path to reviewer guidelines file"
    ),
    output: str = typer.Option(..., help="Output markdown file path"),
    metadata_out: str = typer.Option(None, help="Output JSON metadata file path"),
    max_iters: int = typer.Option(
        3, help="Maximum number of writer-reviewer iterations"
    ),
    accept_threshold: int = typer.Option(
        None,
        min=1,
        max=100,
        help="Score threshold (1-100) for accepting the draft. Default 85. Setting this enables high iteration mode.",
    ),
    index_only: bool = typer.Option(
        False, help="Only index the knowledge base, don't generate documentation"
    ),
    yolo: bool = typer.Option(
        False,
        help="Automatically answer clarifying questions instead of prompting user (YOLO mode)",
    ),
):

    # Setup logging
    setup_logging()

    # Validate inputs
    folder_path = None
    if references_folder:
        folder_path = Path(references_folder)
        if not folder_path.exists() or not folder_path.is_dir():
            console.print(
                f"[red]Error: References folder '{references_folder}' does not exist or is not a directory[/red]"
            )
            raise typer.Exit(1)

    # Read guidelines files
    console.print(f"[blue]Reading guidelines files...[/blue]")
    try:
        with open(writer_guidelines, "r", encoding="utf-8") as f:
            writer_guidelines_content = f.read()
        with open(reviewer_guidelines, "r", encoding="utf-8") as f:
            reviewer_guidelines_content = f.read()
    except FileNotFoundError as e:
        console.print(f"[red]Error: Guidelines file not found: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error reading guidelines files: {e}[/red]")
        raise typer.Exit(1)

    # Initialize feedback loop
    console.print(f"[blue]Initializing AI Writer with LLM: {llm}[/blue]")
    if embedding_provider:
        console.print(f"[blue]Using embedding provider: {embedding_provider}[/blue]")

    loop = FeedbackLoop(
        writer_guidelines=writer_guidelines_content,
        reviewer_guidelines=reviewer_guidelines_content,
        folder_path=str(folder_path) if folder_path else None,
        llm_provider=llm,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        auto_answer_clarifying=yolo,
    )

    # Index only mode
    if index_only:
        if not references_folder:
            console.print(
                "[red]Error: --references-folder is required for --index-only[/red]"
            )
            raise typer.Exit(1)
        console.print("Indexing knowledge base only...")
        loop._ensure_indexed()
        console.print("[green]Knowledge base indexed successfully![/green]")
        return

    # Handle accept threshold and max iterations
    if accept_threshold is None:
        accept_threshold = 85
        final_max_iters = max_iters
        console.print(
            f"[blue]Stopping at score >= {accept_threshold}, max iterations: {final_max_iters}[/blue]"
        )
    else:
        # User provided threshold, enable high iteration mode
        final_max_iters = 1000 if max_iters == 3 else max(1000, max_iters)
        console.print(
            f"[blue]High confidence threshold mode: stopping at score >= {accept_threshold}, max iterations set to {final_max_iters}[/blue]"
        )

    # Run the generation loop
    try:
        draft, metadata = loop.run_loop(
            idea=idea,
            max_iters=final_max_iters,
            accept_threshold=accept_threshold,
            output_file=output,
        )

        if metadata_out:
            metadata_path = Path(metadata_out)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

        # Display results
        score = metadata.get("score", 0)
        iterations = metadata.get("iterations", 0)
        accepted = metadata.get("accepted", False)

        color = "green" if accepted else "yellow"
        status_icon = "✓" if accepted else "⚠"

        result_panel = Panel(
            f"[bold]{status_icon} Documentation generated![/bold]\n\n"
            f"[white]Score: {score}/100[/white]\n"
            f"[white]Iterations: {iterations}[/white]\n"
            f"[white]Accepted: {'Yes' if accepted else 'No'}[/white]\n\n"
            f"[dim]Output: {output}[/dim]\n"
            f"{'[dim]Metadata: ' + metadata_out + '[/dim]' if metadata_out else ''}",
            title="[bold blue]Generation Complete[/bold blue]",
            border_style=color,
        )

        console.print(result_panel)

        # Show a preview of the document
        lines = draft.split("\n")
        preview_lines = lines[:20]  # First 20 lines
        if len(lines) > 20:
            preview_lines.append(f"\n... ({len(lines) - 20} more lines) ...")

        preview_text = "\n".join(preview_lines)
        preview_panel = Panel(
            preview_text, title="[bold]Document Preview[/bold]", border_style="blue"
        )
        console.print(preview_panel)

    except Exception as e:
        console.print(f"[red]Error during generation: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def index(
    folder: str = typer.Option(..., help="Single-folder knowledge base path"),
    embedding_provider: str = typer.Option(
        "openai",
        help="Embedding provider (openai, gemini, huggingface, sentence-transformers)",
    ),
    embedding_model: str = typer.Option(
        None, help="Specific embedding model name (optional, uses provider defaults)"
    ),
):
    """
    Index the knowledge base folder for document retrieval.
    """
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        console.print(
            f"[red]Error: Folder '{folder}' does not exist or is not a directory[/red]"
        )
        raise typer.Exit(1)

    from .indexer import KnowledgeIndexer

    typer.echo(f"Indexing knowledge base: {folder}")
    typer.echo(f"Using embedding provider: {embedding_provider}")

    try:
        indexer = KnowledgeIndexer(
            str(folder_path),
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
        )
        indexer.index_documents()
        typer.echo("Indexing completed successfully!")
    except Exception as e:
        typer.echo(f"Error during indexing: {e}", err=True)
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
