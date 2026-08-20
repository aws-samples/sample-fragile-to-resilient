"""Typed CLI for the summarizer pipeline."""

from pathlib import Path

import typer

from .bedrock_client import ask

app = typer.Typer()


@app.command()
def summarize(file: Path) -> None:
    """Summarize a document with Bedrock."""
    try:
        document = file.read_text()
    except FileNotFoundError:
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(code=1) from None
    summary = ask(f"Summarize this insurance doc in 3 sentences: \n\n{document}")
    print(summary)


if __name__ == "__main__":
    app()
