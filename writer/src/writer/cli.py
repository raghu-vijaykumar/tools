import typer

app = typer.Typer()


@app.callback()
def callback():
    """
    AI documentation generator.
    """
    pass


@app.command()
def run(idea: str = typer.Option(..., help="The idea to document")):
    """
    Run the writer.
    """
    typer.echo(f"Implementing writer for idea: {idea}")
    # TODO: Implement the writer logic


def main():
    app()


if __name__ == "__main__":
    main()
