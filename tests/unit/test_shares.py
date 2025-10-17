# tests/unit/test_shares.py
import pandas as pd
import math

from materia.market import updater as up


def test_estimate_market_shares_missing_columns(capsys):
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    out = up.estimate_market_shares(df)
    assert out == {}
    assert "Missing required columns" in capsys.readouterr().out


def test_estimate_market_shares_zero_total(monkeypatch):
    monkeypatch.setattr(up, "TRADE_ROW_REGIONS", {"US", "CN"}, raising=True)
    df = pd.DataFrame(
        {
            "partneriso": ["FR", "DE", "US", "CN", "W00"],
            "qty": [0, 0, 0, 0, 0],
        }
    )
    assert up.estimate_market_shares(df) == {}


def test_estimate_market_shares_row_and_small_merging(monkeypatch):
    """
    - Columns come in various cases/spaces and are normalized.
    - 'W00' is ignored.
    - US+CN go to RoW bucket.
    - A small partner (<1%) gets merged into RoW.
    """
    monkeypatch.setattr(up, "TRADE_ROW_REGIONS", {"US", "CN"}, raising=True)

    df = pd.DataFrame(
        {
            " PartnerISO ": ["FR", "DE", "US", "CN", "W00"],
            " QTY ": [99.0, 0.5, 6.0, 4.0, 100.0],
        }
    )

    result = up.estimate_market_shares(df)

    assert list(result.keys()) == ["FR", "RoW"]

    assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-12)

    fr_share = 99.0 / (99.0 + 10.5)
    row_share = 10.5 / (99.0 + 10.5)

    assert math.isclose(result["FR"], fr_share, rel_tol=1e-12)
    assert math.isclose(result["RoW"], row_share, rel_tol=1e-12)
