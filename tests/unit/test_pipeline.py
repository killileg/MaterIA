# tests/unit/test_pipeline.py
from pathlib import Path
from materia.epd import pipeline as pl
import xml.etree.ElementTree as ET
import types
import pytest


# print(materia.__file__)


# from epd.path import GEN_PRODUCTS_FOLDER, EPD_FOLDER

# ------------------------------ gen_xml_objects ------------------------------


def test_gen_xml_objects_reads_only_xml(tmp_path: Path):
    # create two valid XMLs and one non-xml
    (tmp_path / "a.xml").write_text("<root/>", encoding="utf-8")
    (tmp_path / "b.xml").write_text("<x><y/></x>", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("nope", encoding="utf-8")

    items = list(pl.gen_xml_objects(tmp_path))
    assert len(items) == 2
    # (path, root)
    assert all(isinstance(p, Path) and isinstance(r, ET.Element) for p, r in items)
    assert {p.name for p, _ in items} == {"a.xml", "b.xml"}  # order not guaranteed


# -------------------------------- gen_epds -----------------------------------


def test_gen_epds_wraps_files_into_IlcdProcess(tmp_path: Path, monkeypatch):
    # prepare real XML files for the folder
    (tmp_path / "p1.xml").write_text("<root id='1'/>", encoding="utf-8")
    (tmp_path / "p2.xml").write_text("<root id='2'/>", encoding="utf-8")

    # point EPD_FOLDER to our tmp dir
    monkeypatch.setattr(pl, "EPD_FOLDER", tmp_path, raising=True)

    created = []

    class FakeIlcd:
        def __init__(self, root, path):
            created.append((path.name, root.tag))

    monkeypatch.setattr(pl, "IlcdProcess", FakeIlcd, raising=True)

    epds = list(pl.gen_epds())
    # two IlcdProcess instances created
    assert len(epds) == 2
    assert {n for n, _ in created} == {"p1.xml", "p2.xml"}


# ----------------------------- gen_filtered_epds -----------------------------


def test_gen_filtered_epds_applies_all_filters():
    class E:
        def __init__(self, v):
            self.v = v

    class F:
        def __init__(self, ok):
            self.ok = ok

        def matches(self, epd):
            return self.ok(epd)

    epds = [E(1), E(2), E(3)]
    filt1 = F(lambda e: e.v >= 2)
    filt2 = F(lambda e: e.v % 2 == 1)  # keep odd
    out = list(pl.gen_filtered_epds(epds, [filt1, filt2]))
    assert [e.v for e in out] == [3]


# ---------------------------- gen_locfiltered_epds ---------------------------


def test_gen_locfiltered_epds_escalates_and_returns(monkeypatch):
    # make LocationFilter a simple container with .locations
    class LF:
        def __init__(self, locs):
            self.locations = set(locs)

    calls = {"n": 0}

    def fake_gen_filtered(epds, filters):
        calls["n"] += 1
        # empty first time, return something on second call
        return [] if calls["n"] == 1 else ["FOUND"]

    monkeypatch.setattr(pl, "LocationFilter", LF, raising=True)
    monkeypatch.setattr(pl, "gen_filtered_epds", fake_gen_filtered, raising=True)
    monkeypatch.setattr(pl, "escalate_location_set", lambda s: s | {"EU"}, raising=True)

    # run
    out = list(pl.gen_locfiltered_epds(epd_roots=[1, 2], filters=[LF({"FR"})]))
    assert out == ["FOUND"]
    assert calls["n"] >= 2  # ensured we escalated once


def test_gen_locfiltered_epds_raises_when_not_found(monkeypatch):
    class LF:
        def __init__(self, locs):
            self.locations = set(locs)

    monkeypatch.setattr(pl, "LocationFilter", LF, raising=True)
    monkeypatch.setattr(pl, "gen_filtered_epds", lambda *_: [], raising=True)
    monkeypatch.setattr(pl, "escalate_location_set", lambda s: s, raising=True)

    with pytest.raises(pl.NoMatchingEPDError):
        list(
            pl.gen_locfiltered_epds(epd_roots=[1], filters=[LF({"XX"})], max_attempts=2)
        )


# -------------------------------- epd_pipeline -------------------------------


def test_epd_pipeline_happy_path(monkeypatch):
    # Fake process with minimal attributes used by epd_pipeline
    process = types.SimpleNamespace(
        matches={"uuids": ["uuid-1"]},
        material_kwargs={"mass": 1.0},
        market={"FR": 0.6, "DE": 0.4},
    )

    # gen_epds -> returns two epd objects with get_lcia_results
    class EpD:
        def __init__(self, name):
            self.name = name
            self.lcia_results = {"GWP": 1}

        def get_lcia_results(self):
            self.lcia_results = {"GWP": 2}

    monkeypatch.setattr(pl, "gen_epds", lambda: [EpD("a"), EpD("b")], raising=True)

    # Filters are built but we don't care about their logic; just accept everything
    monkeypatch.setattr(
        pl, "gen_filtered_epds", lambda epds, f: list(epds), raising=True
    )

    # average/Material plumbing
    monkeypatch.setattr(
        pl, "average_material_properties", lambda epds: {"mass": 2.0}, raising=True
    )

    class FakeMat:
        def __init__(self, **kw):
            self.kw = kw

        def rescale(self, *_):
            pass

        def to_dict(self):
            return self.kw

    monkeypatch.setattr(pl, "Material", FakeMat, raising=True)

    # location filtering: return the same epds for each country
    monkeypatch.setattr(
        pl, "gen_locfiltered_epds", lambda epds, filters: list(epds), raising=True
    )

    # impacts + weighting
    monkeypatch.setattr(
        pl,
        "average_impacts",
        lambda lam: {"GWP": sum(d["GWP"] for d in lam)},
        raising=True,
    )
    monkeypatch.setattr(
        pl,
        "weighted_averages",
        lambda market, imp: {
            "weighted_GWP": sum(
                (
                    (
                        imp[c]["GWP"]
                        if isinstance(imp.get(c), dict)
                        else next(
                            (
                                item["values"].get("A1-A3", 0.0)
                                for item in imp.get(c, [])
                                if item.get("name") == "GWP"
                            ),
                            0.0,
                        )
                    )
                    * w
                )
                for c, w in market.items()
                if c in imp
            )
        },
        raising=True,
    )

    result = pl.epd_pipeline(process)
    # Both epds had GWP=2, bla bla
    assert result == {"weighted_GWP": 4}


def test_gen_xml_objects_handles_invalid_xml(tmp_path, capsys):
    # valid + invalid XML in same folder
    (tmp_path / "good.xml").write_text("<r/>", encoding="utf-8")
    (tmp_path / "bad.xml").write_text(
        "<r>", encoding="utf-8"
    )  # parse error -> except branch

    out = list(pl.gen_xml_objects(tmp_path))
    # only the valid one is yielded
    assert [p.name for p, _ in out] == ["good.xml"]

    # the error was printed by the except block
    captured = capsys.readouterr().out
    assert "Error reading bad.xml" in captured


def test_module_script_bottom_loop_executes(monkeypatch, tmp_path, capsys):
    """
    Execute materia.epd.pipeline as a script so the __main__ block (lines 88–95)
    actually runs and prints the weighted result.
    """
    import runpy

    # Source modules that pipeline imports from
    from materia.io import paths as io_paths
    from materia.epd import models as mdl
    from materia.metrics import averaging as avg_mod
    from materia.core import physics as phys
    from materia.geo import locations as geo_loc

    # --- minimal inputs so both outer loop and epd_pipeline have something to chew
    products_dir = tmp_path / "products"
    products_dir.mkdir()
    (products_dir / "prod.xml").write_text("<root/>", encoding="utf-8")

    epd_dir = tmp_path / "epds"
    epd_dir.mkdir()
    (epd_dir / "epd.xml").write_text("<root/>", encoding="utf-8")

    # pipeline imports these by value at import time
    monkeypatch.setattr(io_paths, "GEN_PRODUCTS_FOLDER", products_dir, raising=True)
    monkeypatch.setattr(io_paths, "EPD_FOLDER", epd_dir, raising=True)

    # keep location escalation simple
    monkeypatch.setattr(geo_loc, "escalate_location_set", lambda m: m, raising=True)

    # Cheap stand-ins used by the pipeline and epd_pipeline()
    class FakeMat:
        def rescale(self, *_a, **_k):
            pass

        def to_dict(self):
            return {"mass": 1.0}

    class FakeIlcd:
        def __init__(self, root, path):
            self.root = root
            self.path = path
            # product process side
            self.matches = ["uuid-1"]
            self.market = {"FR": 1.0}
            self.material_kwargs = {"mass": 1.0}  #
            # EPD side
            self.uuid = "uuid-1"
            self.loc = "FR"
            self.material = FakeMat()

        def get_ref_flow(self):
            pass

        def get_hs_class(self):
            pass

        def get_market(self):
            pass

        def get_matches(self):
            pass

        def get_lcia_results(self):  # used on filtered EPDs
            self.lcia_results = {"GWP": 0.0}

    monkeypatch.setattr(mdl, "IlcdProcess", FakeIlcd, raising=True)

    # averages used inside epd_pipeline()
    monkeypatch.setattr(
        avg_mod,
        "average_material_properties",
        lambda epds: {"mass": 1.0, "volume": 1.0},
        raising=True,
    )
    monkeypatch.setattr(
        avg_mod, "average_impacts", lambda items: {"GWP": 0.0}, raising=True
    )
    monkeypatch.setattr(
        avg_mod,
        "weighted_averages",
        lambda market, impacts: {"weighted_GWP": 0.0},
        raising=True,
    )

    # Material factory used inside epd_pipeline()
    monkeypatch.setattr(phys, "Material", lambda **kw: FakeMat(), raising=True)

    # --- run the module AS A SCRIPT so the __main__ block executes
    runpy.run_module("materia.epd.pipeline", run_name="__main__")

    # pprint(weighted) should have printed our key
    assert capsys.readouterr().out.strip() != ""
