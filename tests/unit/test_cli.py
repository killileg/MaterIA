# tests/unit/test_cli.py
import json
from click.testing import CliRunner
from materia import cli


def _setup_dirs(tmp_path):
    gen = tmp_path / "gen"
    epd = tmp_path / "epds"
    gen.mkdir()
    epd.mkdir()
    return gen, epd


def test_default_output(monkeypatch, tmp_path):
    """No -o flag → writes to ../output_generic/"""
    runner = CliRunner()
    gen, epd = _setup_dirs(tmp_path)
    monkeypatch.setattr(
        cli, "run_materia", lambda *_: ({"mass": 1}, "uuid"), raising=True
    )

    result = runner.invoke(cli.main, [str(gen), str(epd)])
    out_file = gen.parent / "output_generic" / "uuid_output.json"

    assert result.exit_code == 0
    assert out_file.exists()
    assert json.loads(out_file.read_text()) == {"mass": 1}
    assert "No output path provided" in result.output


def test_with_output_path(monkeypatch, tmp_path):
    """With -o flag → writes exactly there."""
    runner = CliRunner()
    gen, epd = _setup_dirs(tmp_path)
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        cli, "run_materia", lambda *_: ({"GWP": 2.5}, "abc"), raising=True
    )

    result = runner.invoke(cli.main, [str(gen), str(epd), "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert json.loads(out.read_text()) == {"GWP": 2.5}
    assert "Output has been written" in result.output


def test_file_input_triggers_mkdir(monkeypatch, tmp_path):
    """File input → creates parent/output_generic and writes JSON."""
    runner = CliRunner()
    gen, epd = _setup_dirs(tmp_path)
    xml = gen / "p.xml"
    xml.write_text("<r/>")

    called = {"mkdir": False}
    real_mkdir = cli.Path.mkdir

    def spy_mkdir(self, *a, **k):
        if self.name == "output_generic":
            called["mkdir"] = True
        return real_mkdir(self, *a, **k)

    monkeypatch.setattr(cli.Path, "mkdir", spy_mkdir, raising=True)

    monkeypatch.setattr(
        cli, "run_materia", lambda *_: ({"mass": 3}, "uuid2"), raising=True
    )

    result = runner.invoke(cli.main, [str(xml), str(epd)])
    out = gen.parent / "output_generic" / "uuid2_output.json"

    assert result.exit_code == 0
    assert out.exists()
    assert called["mkdir"] is True
    assert json.loads(out.read_text()) == {"mass": 3}
