# tests/unit/test_averaging.py
import pytest
from materia.metrics import averaging as avg


# ----------------------------- average_impacts ------------------------------


def test_average_impacts_basic(monkeypatch):
    # Mock to_float to test summing and counting logic
    monkeypatch.setattr(avg, "to_float", float)

    impacts_list = [
        [
            {"name": "GWP", "values": {"A1": 10.0, "A2": 20.0}},
            {"name": "ODP", "values": {"A1": 5.0}},
        ],
        [
            {"name": "GWP", "values": {"A1": 30.0, "A2": 40.0}},
            {"name": "ODP", "values": {"A1": 15.0}},
        ],
    ]

    result = avg.average_impacts(impacts_list, decimals=2)

    # Expect average: GWP A1=(10+30)/2=20, A2=(20+40)/2=30
    gwp = next(r for r in result if r["name"] == "GWP")
    assert gwp["values"] == {"A1": 20.0, "A2": 30.0}

    odp = next(r for r in result if r["name"] == "ODP")
    assert odp["values"] == {"A1": 10.0}


def test_average_impacts_skips_non_numeric(monkeypatch):
    monkeypatch.setattr(avg, "to_float", lambda v: v)
    impacts_list = [
        [{"name": "X", "values": {"A1": "bad", "A2": 5.0}}],
    ]
    res = avg.average_impacts(impacts_list)
    assert res[0]["values"] == {"A2": 5.0}


# ----------------------------- weighted_averages -----------------------------


def test_weighted_averages_simple_case():
    market = {"FR": 0.6, "DE": 0.4}
    results = {
        "FR": [
            {"name": "GWP", "values": {"A1": 10.0, "A2": 20.0}},
            {"name": "ODP", "values": {"A1": 5.0}},
        ],
        "DE": [
            {"name": "GWP", "values": {"A1": 30.0, "A2": 40.0}},
            {"name": "ODP", "values": {"A1": 15.0}},
        ],
    }

    weighted = avg.weighted_averages(market, results)
    # Weighted mean: FR(0.6) * 10 + DE(0.4) * 30 = 18 for A1
    assert pytest.approx(weighted["GWP"]["A1"], rel=1e-6) == 18.0
    assert pytest.approx(weighted["GWP"]["A2"], rel=1e-6) == 28.0
    assert pytest.approx(weighted["ODP"]["A1"], rel=1e-6) == 9.0


def test_weighted_averages_missing_country():
    market = {"FR": 1.0, "DE": 0.4}
    results = {
        "FR": [{"name": "GWP", "values": {"A1": 5.0}}],
        # "DE" missing -> should just use FR
    }
    weighted = avg.weighted_averages(market, results)
    assert weighted["GWP"]["A1"] == 5.0


def test_weighted_averages_empty_inputs():
    assert avg.weighted_averages({}, {}) == {}


# ----------------------------- average_material_properties ------------------


class DummyMat:
    def __init__(self, d):
        self._d = d

    def to_dict(self):
        return self._d


class DummyEpd:
    def __init__(self, d):
        self.material = DummyMat(d)


def test_average_material_properties_basic():
    epds = [
        DummyEpd({"mass": 10.0, "volume": 2.0, "text": "skip"}),
        DummyEpd({"mass": 20.0, "volume": 4.0}),
    ]
    res = avg.average_material_properties(epds, decimals=2)
    # average: mass = 15.0, volume = 3.0
    assert res == {"mass": 15.0, "volume": 3.0}


def test_average_material_properties_handles_empty():
    epds = [DummyEpd({"non_numeric": "x"}), DummyEpd({})]
    assert avg.average_material_properties(epds) == {}
