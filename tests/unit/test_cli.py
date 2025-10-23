# tests/unit/test_cli.py
import json
from click.testing import CliRunner

from materia import cli


def test_main_default_output_creates_file(monkeypatch, tmp_path):
    """
    No --output_path: writes to <input_path>/../output_generic/<uuid>_output.json
    and echoes a message.
    """
    runner = CliRunner()

    input_dir = tmp_path / "gen"
    epd_dir = tmp_path / "epds"
    input_dir.mkdir()
    epd_dir.mkdir()

    # run_materia now returns (average, uuid)
    monkeypatch.setattr(
        cli, "run_materia", lambda a, b: ({"mass": 1.0}, "uuid-123"), raising=True
    )

    result = runner.invoke(cli.main, [str(input_dir), str(epd_dir)])
    assert result.exit_code == 0

    out_folder = input_dir.parent / "output_generic"
    out_file = out_folder / "uuid-123_output.json"
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data == {"mass": 1.0}

    assert "Received path" in result.output
    assert "No output path provided. File created at" in result.output


def test_main_writes_to_given_output(monkeypatch, tmp_path):
    """
    With --output_path: writes JSON there and echoes the path.
    """
    runner = CliRunner()

    input_dir = tmp_path / "gen"
    epd_dir = tmp_path / "epds"
    input_dir.mkdir()
    epd_dir.mkdir()
    out_file = tmp_path / "out.json"

    monkeypatch.setattr(
        cli, "run_materia", lambda a, b: ({"GWP": 2.5}, "abc-uuid"), raising=True
    )

    result = runner.invoke(
        cli.main, [str(input_dir), str(epd_dir), "-o", str(out_file)]
    )
    assert result.exit_code == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data == {"GWP": 2.5}
    assert "Output has been written in" in result.output
