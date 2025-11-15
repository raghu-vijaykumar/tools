import typer

app = typer.Typer()


@app.callback()
def callback():
    """
    My Tools CLI - Aggregator for all tools.
    """
    pass


@app.command()
def newsletter(days: int = 7, provider: str = "gemini"):
    """
    Run the newsletter fetcher.
    """
    import newsletter.main as nl

    # nl.main(["--days", str(days), "--provider", provider])
    typer.echo(f"Running newsletter with days={days}, provider={provider}")
    # Call the function directly


@app.command()
def writer():
    """
    Run the writer tool.
    """
    typer.echo("Writer tool not implemented yet.")


if __name__ == "__main__":
    app()
