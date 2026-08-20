from pathlib import Path

import pytest
from typer.testing import CliRunner

import fde.cli
from fde.cli import app

runner = CliRunner()


def test_summarize_prints_summary_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("a small policy document")
    monkeypatch.setattr(fde.cli, "ask", lambda prompt: "the summary")

    result = runner.invoke(app, [str(doc)])

    assert result.exit_code == 0
    assert "the summary" in result.output


def test_summarize_missing_file_exits_one_with_stderr_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(prompt: str) -> str:
        raise AssertionError("ask() must not be called for a missing file")

    monkeypatch.setattr(fde.cli, "ask", explode)

    result = runner.invoke(app, ["missing.txt"])

    assert result.exit_code == 1
    assert "file not found: missing.txt" in result.stderr
    assert "file not found" not in result.stdout


def test_summarize_sends_document_inside_the_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("UNIQUE-DOC-CONTENT")
    seen: list[str] = []

    def capture(prompt: str) -> str:
        seen.append(prompt)
        return "ok"

    monkeypatch.setattr(fde.cli, "ask", capture)

    result = runner.invoke(app, [str(doc)])

    assert result.exit_code == 0
    assert len(seen) == 1
    assert "UNIQUE-DOC-CONTENT" in seen[0]
