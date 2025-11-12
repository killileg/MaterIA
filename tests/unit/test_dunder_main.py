# tests/unit/test_dunder_main.py
import runpy
import types
import sys


def test_dunder_main_invokes_cli_main(monkeypatch, capsys):
    called = {"n": 0}

    def fake_main():
        called["n"] += 1
        print("CLI MAIN CALLED")

    # Provide a fake `materia.cli` with our stubbed `main`
    fake_cli = types.SimpleNamespace(main=fake_main)
    monkeypatch.setitem(sys.modules, "materia_epd.cli", fake_cli)

    # Run the package as a script -> __name__ == "__main__"
    runpy.run_module("materia_epd.__main__", run_name="__main__")

    assert called["n"] == 1
    assert "CLI MAIN CALLED" in capsys.readouterr().out


def test_importing_module_does_not_call_main(monkeypatch):
    called = {"n": 0}

    def fake_main():
        called["n"] += 1

    fake_cli = types.SimpleNamespace(main=fake_main)
    monkeypatch.setitem(sys.modules, "materia_epd.cli", fake_cli)

    # Import in normal mode -> __name__ != "__main__" (no call)
    # Clear any cached entry so the module executes fresh.
    sys.modules.pop("materia_epd.__main__", None)
    runpy.run_module("materia_epd.__main__", run_name="not_main")

    assert called["n"] == 0
