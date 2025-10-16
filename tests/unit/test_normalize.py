# tests/unit/test_normalize.py
import xml.etree.ElementTree as ET
import pytest

from materia.metrics import normalize as norm


@pytest.fixture(autouse=True)
def patch_constants(monkeypatch):
    # Minimal constants so we can craft tiny XMLs
    monkeypatch.setattr(norm, "EPD_NS", {"epd": "urn:test:epd"}, raising=True)
    monkeypatch.setattr(
        norm,
        "LCIA_OUTPUT_MODULES",
        ["A1", "A2", "A1-A3", "B1"],
        raising=True,
    )
    monkeypatch.setattr(
        norm,
        "LCIA_AGGREGATE_MAP",
        {"A1-A3": ["A1", "A2"]},  # aggregate A1 + A2
        raising=True,
    )


def _amount(module, text):
    """Build an <amount> element with namespaced @epd:module attr."""
    el = ET.Element("amount")
    el.attrib[f"{{{norm.EPD_NS['epd']}}}module"] = module
    el.text = text
    return el


def test_normalize_direct_and_aggregate(monkeypatch):
    # Use real to_float
    monkeypatch.setattr(norm, "to_float", float, raising=True)

    amounts = [
        _amount("A1", "10.0"),
        _amount("A2", "30.0"),
    ]
    out = norm.normalize_module_values(amounts)  # scaling_factor=1.0
    # Direct modules present
    assert out["A1"] == 10.0
    assert out["A2"] == 30.0
    # Aggregated A1-A3 = A1 + A2
    assert out["A1-A3"] == 40.0
    # Module in outputs but not present and not aggregable -> None
    assert out["B1"] is None  # not provided and no aggregate parts


def test_normalize_applies_scaling_factor(monkeypatch):
    monkeypatch.setattr(norm, "to_float", float, raising=True)

    amounts = [_amount("A1", "2.5")]
    out = norm.normalize_module_values(amounts, scaling_factor=4.0)
    assert out["A1"] == pytest.approx(10.0)  # 2.5 * 4


def test_normalize_aggregate_all_missing_returns_none(monkeypatch):
    # If aggregate parts exist but all are None/invalid -> None
    def bad_to_float(x):
        return None  # force invalid conversion

    monkeypatch.setattr(norm, "to_float", bad_to_float, raising=True)

    amounts = [_amount("A1", "bad"), _amount("A2", None)]
    out = norm.normalize_module_values(amounts)
    assert out["A1"] is None
    assert out["A2"] is None
    # Aggregate A1-A3 should be None because no valid parts
    assert out["A1-A3"] is None


def test_normalize_non_numeric_is_skipped(monkeypatch):
    # Mix valid and invalid values; invalid should not contribute
    monkeypatch.setattr(
        norm,
        "to_float",
        lambda v: float(v) if v.replace(".", "", 1).isdigit() else None,
        raising=True,
    )

    amounts = [_amount("A1", "5.0"), _amount("A2", "oops")]
    out = norm.normalize_module_values(amounts)
    assert out["A1"] == 5.0
    assert out["A2"] is None
    # Aggregate (A1-A3) should equal only valid part
    assert out["A1-A3"] == 5.0
