# tests/unit/test_comtrade.py
import os
import sys
import types
import pandas as pd

# ---------------------------------------------------------------------------
# Inject a fake `comtradeapicall` module BEFORE importing comtrade.py
# ---------------------------------------------------------------------------
FakeAPI = types.SimpleNamespace()
FakeAPI.payload = pd.DataFrame([{"x": 1}, {"x": 2}])  # default payload
FakeAPI.exc = None


def _fake_getFinalData(_key, **_params):
    # Ensure the function under test forwards the key correctly
    assert _key == "FAKE_API_KEY", f"Unexpected API key: {_key}"
    if FakeAPI.exc is not None:
        raise FakeAPI.exc
    return FakeAPI.payload


FakeAPI.getFinalData = _fake_getFinalData
sys.modules["comtradeapicall"] = FakeAPI  # what comtrade.py imports

# Now import the system under test (it will bind to our FakeAPI)
from materia.market import comtrade as ct  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_get_unique_hs_codes_collects_from_jsons(monkeypatch, tmp_path):
    monkeypatch.setattr(ct.IO_PATHS, "GEN_PRODUCTS_FOLDER", tmp_path, raising=True)

    def fake_gen_json_objects(_folder):
        yield tmp_path / "a.json", {"HS Code": "1234", "other": 1}
        yield tmp_path / "b.json", {"HS Code": "5678"}
        yield tmp_path / "c.json", {"nope": True}  # ignored
        yield tmp_path / "d.json", ["not-a-dict"]  # ignored
        yield tmp_path / "e.json", {"HS Code": "1234"}  # duplicate

    monkeypatch.setattr(ct, "gen_json_objects", fake_gen_json_objects, raising=True)

    codes = ct.get_unique_hs_codes()
    assert codes == {"1234", "5678"}


def _base_patches(monkeypatch, tmp_path):
    """Common test setup (patch time.sleep, folders, constants)."""
    os.makedirs(tmp_path, exist_ok=True)
    monkeypatch.setattr(ct.IO_PATHS, "IMPORTS_FOLDER", str(tmp_path), raising=True)
    monkeypatch.setattr(
        ct,
        "time",
        type("T", (), {"sleep": staticmethod(lambda *_: None)})(),
        raising=True,
    )
    monkeypatch.setattr(ct.C, "TRADE_YEARS", ["2021", "2022"], raising=True)
    monkeypatch.setattr(ct.C, "TRADE_TARGET", "250", raising=True)
    monkeypatch.setattr(ct.C, "TRADE_FLOW", "M", raising=True)


def test_fetch_trade_data_writes_csv_on_success(monkeypatch, tmp_path):
    _base_patches(monkeypatch, tmp_path)

    # Non-empty payload -> should write CSV
    FakeAPI.payload = pd.DataFrame([{"x": 1}, {"x": 2}])

    out = ct.fetch_trade_data_for_hs_code("1234", "FAKE_API_KEY")
    assert out is not None
    assert os.path.basename(out) == "I_1234.csv"

    read = pd.read_csv(out)
    assert list(read["x"]) == [1, 2]


def test_fetch_trade_data_returns_none_when_empty(monkeypatch, tmp_path, capsys):
    _base_patches(monkeypatch, tmp_path)

    # Empty payload -> should print and return None
    FakeAPI.payload = pd.DataFrame()

    out = ct.fetch_trade_data_for_hs_code("9999", "FAKE_API_KEY")
    assert out is None
    assert "No data for HS 9999" in capsys.readouterr().out


def test_fetch_trade_data_handles_exception(monkeypatch, tmp_path, capsys):
    _base_patches(monkeypatch, tmp_path)

    # Raise from API -> should catch and return None
    FakeAPI.exc = RuntimeError("boom")

    out = ct.fetch_trade_data_for_hs_code("1111", "FAKE_API_KEY")
    assert out is None
    output = capsys.readouterr().out
    assert "Error fetching data for HS 1111: boom" in output

    # Reset for good hygiene
    FakeAPI.exc = None
