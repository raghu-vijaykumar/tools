import typer
import logging
from common.logging import setup_logging

app = typer.Typer()


newsletter_app = typer.Typer()
app.add_typer(newsletter_app, name="newsletter", help="Newsletter tools")


@newsletter_app.callback()
def newsletter_callback():
    """
    Newsletter management tools.
    """
    pass


@app.callback()
def callback():
    """
    My Tools CLI - Aggregator for all tools.
    """
    setup_logging()
    logging.info("CLI initialized and ready to execute commands")


@newsletter_app.command("run")
def newsletter_run(
    provider: str = typer.Option("gemini", help="LLM provider to use"),
    tts: str = typer.Option("gtts", help="TTS model or provider to use"),
    no_audio: bool = typer.Option(False, help="Skip audio generation"),
    no_linkedin: bool = typer.Option(False, help="Skip LinkedIn posting"),
    limit_website: str = typer.Option(None, help="Limit fetching to specific website (e.g., 'uber' for scraping, or 'github' for RSS)"),
):
    """
    Run the newsletter fetcher.
    """
    logging.info(
        f"Executing newsletter run command, provider={provider}, tts={tts}, no_audio={no_audio}, no_linkedin={no_linkedin}, limit_website={limit_website}"
    )

    try:
        import newsletter.main as nl

        # Call the newsletter run_newsletter function directly
        nl.run_newsletter(
            provider=provider,
            tts=tts,
            no_audio=no_audio,
            no_linkedin=no_linkedin,
            limit_website=limit_website,
        )
    except Exception as e:
        typer.echo(f"Error running newsletter: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def writer(ctx: typer.Context):
    """
    Run the writer tool.
    """
    logging.info("Executing writer command - delegating to writer CLI")
    # Import and run the writer CLI
    from writer.cli import app as writer_app

    # Pass the remaining arguments to the writer CLI
    writer_app()


if __name__ == "__main__":
    app()
