# tests/unit/test_market.py
import sys
import types
import pandas as pd
from pathlib import Path

# ---- Fake API module injected before importing updater ----
FakeAPI = types.SimpleNamespace()
FakeAPI.payload = pd.DataFrame([{"x": 1}, {"x": 2}])
FakeAPI.exc = None


def _fake_getFinalData(key, **params):
    assert key == "FAKE_API_KEY"
    if FakeAPI.exc:
        raise FakeAPI.exc
    return FakeAPI.payload


FakeAPI.getFinalData = _fake_getFinalData
sys.modules["comtradeapicall"] = FakeAPI

from materia.market import updater as up  # noqa: E402


def test_get_unique_hs_codes(monkeypatch, tmp_path):
    # Replace the whole IO_PATHS module with a minimal stub exposing GEN_PRODUCTS_FOLDER
    io_stub = types.SimpleNamespace(GEN_PRODUCTS_FOLDER=tmp_path)
    monkeypatch.setattr(up, "IO_PATHS", io_stub, raising=False)

    def fake_gen_json_objects(_):
        yield Path("a.json"), {"HS Code": "1234"}
        yield Path("b.json"), {"HS Code": "5678"}
        yield Path("c.json"), {"nope": True}
        yield Path("d.json"), ["not-a-dict"]

    monkeypatch.setattr(up, "gen_json_objects", fake_gen_json_objects, raising=True)
    assert up.get_unique_hs_codes() == {"1234", "5678"}


def test_fetch_trade_data(monkeypatch):
    monkeypatch.setattr(up.C, "TRADE_YEARS", ["2021"], raising=True)
    monkeypatch.setattr(up.C, "TRADE_TARGET", "250", raising=True)
    monkeypatch.setattr(up.C, "TRADE_FLOW", "M", raising=True)
    monkeypatch.setattr(
        up, "time", types.SimpleNamespace(sleep=lambda *_: None), raising=True
    )

    FakeAPI.payload = pd.DataFrame([{"x": 1}])
    df = up.fetch_trade_data_for_hs_code("1234", "FAKE_API_KEY")
    assert isinstance(df, pd.DataFrame)


def test_fetch_trade_data_empty(monkeypatch, capsys):
    monkeypatch.setattr(up.C, "TRADE_YEARS", ["2021"], raising=True)
    monkeypatch.setattr(up.C, "TRADE_TARGET", "250", raising=True)
    monkeypatch.setattr(up.C, "TRADE_FLOW", "M", raising=True)
    monkeypatch.setattr(
        up, "time", types.SimpleNamespace(sleep=lambda *_: None), raising=True
    )

    FakeAPI.payload = pd.DataFrame()
    df = up.fetch_trade_data_for_hs_code("9999", "FAKE_API_KEY")
    assert df is None
    assert "No data for HS 9999" in capsys.readouterr().out


def test_fetch_trade_data_exception(monkeypatch, capsys):
    monkeypatch.setattr(up.C, "TRADE_YEARS", ["2021"], raising=True)
    monkeypatch.setattr(up.C, "TRADE_TARGET", "250", raising=True)
    monkeypatch.setattr(up.C, "TRADE_FLOW", "M", raising=True)
    monkeypatch.setattr(
        up, "time", types.SimpleNamespace(sleep=lambda *_: None), raising=True
    )

    FakeAPI.exc = RuntimeError("boom")
    df = up.fetch_trade_data_for_hs_code("1111", "FAKE_API_KEY")
    assert df is None
    assert "Error fetching data for HS 1111: boom" in capsys.readouterr().out
    FakeAPI.exc = None


def test_estimate_market_shares():
    df = pd.DataFrame({"partneriso": ["A", "B", "E19"], "qty": [100, 50, 30]})
    shares = up.estimate_market_shares(df)
    assert isinstance(shares, dict)
    assert "RoW" in shares or "A" in shares


def test_update_shares(monkeypatch):
    monkeypatch.setattr(up, "get_unique_hs_codes", lambda: {"1234"}, raising=True)
    monkeypatch.setattr(
        up,
        "fetch_trade_data_for_hs_code",
        lambda hs, key: pd.DataFrame({"partneriso": ["A", "E19"], "qty": [100, 50]}),
        raising=True,
    )
    monkeypatch.setattr(
        up, "estimate_market_shares", lambda df: {"A": 0.67, "RoW": 0.33}, raising=True
    )
    monkeypatch.setattr(up, "tqdm", lambda x, **kwargs: x, raising=True)

    calls = []

    def fake_update_user_data(subfolder, filename, data):
        calls.append((subfolder, filename, data))

    monkeypatch.setattr(up, "update_user_data", fake_update_user_data, raising=True)
    up.update_shares("FAKE_API_KEY")

    assert calls == [("market_shares", "1234.json", {"A": 0.67, "RoW": 0.33})]
