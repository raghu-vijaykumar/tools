import typer

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
    pass


@newsletter_app.command("run")
def newsletter_run(
    days: int = 1,
    provider: str = typer.Option("gemini", help="LLM provider to use"),
    tts: str = typer.Option("gtts", help="TTS model or provider to use"),
    cleanup: bool = typer.Option(True, help="Clean up data directory after processing"),
):
    """
    Run the newsletter fetcher.
    """
    import newsletter.main as nl

    try:
        # Call the newsletter run_newsletter function directly
        nl.run_newsletter(days=days, provider=provider, tts=tts, cleanup=cleanup)
    except Exception as e:
        typer.echo(f"Error running newsletter: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def writer():
    """
    Run the writer tool.
    """
    typer.echo("Writer tool not implemented yet.")


if __name__ == "__main__":
    app()
