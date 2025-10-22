# tests/unit/test_cli.py
import json
from click.testing import CliRunner

from materia import cli


def test_main_prints_average(monkeypatch, tmp_path):
    """Covers the branch without output_path (prints to terminal)."""
    runner = CliRunner()

    # stub run_materia to avoid real work
    monkeypatch.setattr(cli, "run_materia", lambda p: {"mass": 1.0}, raising=True)

    # run the CLI
    result = runner.invoke(cli.main, [str(tmp_path)])
    assert result.exit_code == 0
    # printed the fake data
    assert "Received path" in result.output
    assert "'mass': 1.0" in result.output


def test_main_writes_output(monkeypatch, tmp_path):
    """Covers the branch with output_path set."""
    runner = CliRunner()
    out_file = tmp_path / "out.json"

    monkeypatch.setattr(cli, "run_materia", lambda p: {"GWP": 2.5}, raising=True)

    # run CLI with -o option
    result = runner.invoke(cli.main, [str(tmp_path), "-o", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    # JSON content matches our fake result
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data == {"GWP": 2.5}
    assert "Output has been written" in result.output
