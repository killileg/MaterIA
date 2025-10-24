# tests/unit/test_cli.py
from pathlib import Path
from click.testing import CliRunner
from materia import cli


def _setup_dirs(tmp_path: Path):
    gen = tmp_path / "gen"
    epd = tmp_path / "epds"
    gen.mkdir()
    epd.mkdir()
    return gen, epd


def test_no_output_path_calls_pipeline_with_none(monkeypatch, tmp_path):
    runner = CliRunner()
    gen, epd = _setup_dirs(tmp_path)

    called = {}

    def fake_run_materia(a, b, c):
        called["a"] = a
        called["b"] = b
        called["c"] = c  # should be None

    monkeypatch.setattr(cli, "run_materia", fake_run_materia, raising=True)

    result = runner.invoke(cli.main, [str(gen), str(epd)])
    assert result.exit_code == 0
    assert "Received path:" in result.output
    assert called["a"] == gen
    assert called["b"] == epd
    assert called["c"] is None


def test_with_output_path_calls_pipeline_with_path(monkeypatch, tmp_path):
    runner = CliRunner()
    gen, epd = _setup_dirs(tmp_path)
    out = tmp_path / "out" / "file.xml"  # could be file or folder; pipeline decides

    called = {}

    def fake_run_materia(a, b, c):
        called["a"] = a
        called["b"] = b
        called["c"] = c  # should be Path

    monkeypatch.setattr(cli, "run_materia", fake_run_materia, raising=True)

    result = runner.invoke(cli.main, [str(gen), str(epd), "-o", str(out)])
    assert result.exit_code == 0
    assert called["a"] == gen
    assert called["b"] == epd
    assert called["c"] == out
