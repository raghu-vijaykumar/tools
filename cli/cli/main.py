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
    days: int = typer.Option(1, help="Number of days to fetch (default: 1)"),
    dates: str = typer.Option(
        None,
        help="Comma-separated dates or ranges (e.g., '2023-01-01,2023-01-02' or '2023-01-01 to 2023-01-03')",
    ),
    provider: str = typer.Option("gemini", help="LLM provider to use"),
    tts: str = typer.Option("gtts", help="TTS model or provider to use"),
    cleanup: bool = typer.Option(True, help="Clean up data directory after processing"),
    no_audio: bool = typer.Option(False, help="Skip audio generation"),
):
    """
    Run the newsletter fetcher.
    """
    from common.config import parse_dates

    import newsletter.main as nl

    # Determine dates to process
    dates_list = None
    if dates:
        dates_list = parse_dates(dates)
        logging.info(
            f"Executing newsletter run command for specific dates: {dates_list}, provider={provider}, tts={tts}, cleanup={cleanup}, no_audio={no_audio}"
        )
    else:
        logging.info(
            f"Executing newsletter run command for last {days} days, provider={provider}, tts={tts}, cleanup={cleanup}, no_audio={no_audio}"
        )

    try:
        # Call the newsletter run_newsletter function directly
        nl.run_newsletter(
            days=days,
            dates_list=dates_list,
            provider=provider,
            tts=tts,
            cleanup=cleanup,
            no_audio=no_audio,
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
