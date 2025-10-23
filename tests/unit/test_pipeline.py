# tests/unit/test_pipeline.py
from pathlib import Path
import types
import xml.etree.ElementTree as ET
import pytest

from materia.epd import pipeline as pl


# ------------------------------ gen_xml_objects ------------------------------


def test_gen_xml_objects_with_folder_reads_xml_only(tmp_path: Path):
    (tmp_path / "a.xml").write_text("<a/>", encoding="utf-8")
    (tmp_path / "b.xml").write_text("<b/>", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("x", encoding="utf-8")

    out = list(pl.gen_xml_objects(tmp_path))
    names = {p.name for p, _ in out}
    assert names == {"a.xml", "b.xml"}
    assert all(isinstance(root, ET.Element) for _, root in out)  # parsed roots


def test_gen_xml_objects_with_file_uses_parent(tmp_path: Path):
    (tmp_path / "x1.xml").write_text("<r/>", encoding="utf-8")
    (tmp_path / "x2.xml").write_text("<r/>", encoding="utf-8")
    file_inside = tmp_path / "x1.xml"

    out = list(pl.gen_xml_objects(file_inside))
    names = {p.name for p, _ in out}
    assert names == {"x1.xml", "x2.xml"}


def test_gen_xml_objects_invalid_path_raises(tmp_path: Path):
    bogus = tmp_path / "does_not_exist.anything"
    with pytest.raises(ValueError):
        list(pl.gen_xml_objects(bogus))


def test_gen_xml_objects_skips_bad_xml(tmp_path: Path, capsys):
    (tmp_path / "ok.xml").write_text("<r/>", encoding="utf-8")
    (tmp_path / "bad.xml").write_text("<r>", encoding="utf-8")  # malformed

    out = list(pl.gen_xml_objects(tmp_path))
    assert [p.name for p, _ in out] == ["ok.xml"]
    msg = capsys.readouterr().out
    assert "Error reading bad.xml" in msg


# -------------------------------- gen_epds -----------------------------------


def test_gen_epds_wraps_xmls_in_IlcdProcess(tmp_path: Path, monkeypatch):
    (tmp_path / "p1.xml").write_text("<root id='1'/>", encoding="utf-8")
    (tmp_path / "p2.xml").write_text("<root id='2'/>", encoding="utf-8")

    calls = []

    class FakeIlcd:
        def __init__(self, root, path):
            calls.append((path.name, root.tag))

    monkeypatch.setattr(pl, "IlcdProcess", FakeIlcd, raising=True)
    out = list(pl.gen_epds(tmp_path))
    assert len(out) == 2
    assert {n for n, _ in calls} == {"p1.xml", "p2.xml"}


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

    epds = [E(1), E(2), E(3), E(4)]
    f1 = F(lambda e: e.v >= 2)
    f2 = F(lambda e: e.v % 2 == 0)
    out = list(pl.gen_filtered_epds(epds, [f1, f2]))
    assert [e.v for e in out] == [2, 4]


# ---------------------------- gen_locfiltered_epds ---------------------------


def test_gen_locfiltered_epds_escalates_until_found(monkeypatch):
    # minimal LocationFilter with .locations
    class LF:
        def __init__(self, locs):
            self.locations = set(locs)

    # First attempt returns [], second attempt returns sentinel
    attempts = {"n": 0}

    def fake_gen_filtered(epds, filters):
        attempts["n"] += 1
        return [] if attempts["n"] == 1 else ["FOUND"]

    monkeypatch.setattr(pl, "LocationFilter", LF, raising=True)
    monkeypatch.setattr(pl, "gen_filtered_epds", fake_gen_filtered, raising=True)
    monkeypatch.setattr(pl, "escalate_location_set", lambda s: s | {"EU"}, raising=True)

    out = list(pl.gen_locfiltered_epds(epd_roots=[1, 2], filters=[LF({"FR"})]))
    assert out == ["FOUND"]
    assert attempts["n"] >= 2  # ensured escalation path executed


def test_gen_locfiltered_epds_raises_when_not_found(monkeypatch):
    class LF:
        def __init__(self, locs):
            self.locations = set(locs)

    monkeypatch.setattr(pl, "LocationFilter", LF, raising=True)
    monkeypatch.setattr(pl, "gen_filtered_epds", lambda *_: [], raising=True)
    monkeypatch.setattr(pl, "escalate_location_set", lambda s: s, raising=True)

    with pytest.raises(pl.NoMatchingEPDError):
        list(pl.gen_locfiltered_epds([1], [LF({"XX"})], max_attempts=2))


# -------------------------------- epd_pipeline -------------------------------


def test_epd_pipeline_happy_path(monkeypatch, tmp_path: Path):
    # process stub with required attributes
    process = types.SimpleNamespace(
        matches={"uuids": ["u1"]},
        material_kwargs={"mass": 1.0},
        market={"FR": 0.7, "DE": 0.3},
    )

    # EPD objects that the pipeline will operate on
    class EPD:
        def __init__(self, name):
            self.name = name
            self.lcia_results = {"GWP": 1}

        def get_lcia_results(self):
            # simulate computation
            self.lcia_results = {"GWP": 2}

    # gen_epds returns two epds
    monkeypatch.setattr(
        pl, "gen_epds", lambda folder: [EPD("a"), EPD("b")], raising=True
    )
    # gen_filtered_epds passes both through (UUID/unit filters abstracted)
    monkeypatch.setattr(
        pl, "gen_filtered_epds", lambda epds, f: list(epds), raising=True
    )

    # average material props → build Material → rescale → to_dict
    monkeypatch.setattr(
        pl, "average_material_properties", lambda epds: {"mass": 2.0}, raising=True
    )

    class FakeMat:
        def __init__(self, **kw):
            self.kw = dict(kw)

        def rescale(self, *_):
            pass

        def to_dict(self):
            return self.kw

    monkeypatch.setattr(pl, "Material", FakeMat, raising=True)

    # each market country gets epds; then impacts averaged and weighted
    monkeypatch.setattr(
        pl, "gen_locfiltered_epds", lambda epds, filters: list(epds), raising=True
    )
    monkeypatch.setattr(
        pl,
        "average_impacts",
        lambda lst: {"GWP": sum(d["GWP"] for d in lst) / len(lst)},
        raising=True,
    )
    monkeypatch.setattr(
        pl,
        "weighted_averages",
        lambda market, imp: {
            "weighted_GWP": sum(imp[c]["GWP"] * w for c, w in market.items())
        },
        raising=True,
    )

    # path_to_epd_folder is joined with "processes" inside pipeline (we don't need FS)
    epd_root = tmp_path  # not used by the stubs, but satisfies the interface
    result = pl.epd_pipeline(process, epd_root)
    assert result == {
        "weighted_GWP": 2
    }  # 2 epds → GWP=2 per country → weighted sum = 2


# -------------------------------- run_materia --------------------------------


def test_run_materia_executes_pipeline_and_returns_uuid(monkeypatch, tmp_path: Path):
    # Prepare product folder (input) and epd folder (target)
    prod_dir = tmp_path / "products"
    epd_dir = tmp_path / "epds"
    prod_dir.mkdir()
    epd_dir.mkdir()

    # gen_xml_objects should yield exactly one "product" root
    def fake_gen_xml_objects(folder):
        assert Path(folder) == prod_dir  # run_materia passes this in
        yield (prod_dir / "prod.xml", ET.Element("root"))

    monkeypatch.setattr(pl, "gen_xml_objects", fake_gen_xml_objects, raising=True)

    # IlcdProcess minimal with attributes/methods used in run_materia
    class FakeIlcd:
        def __init__(self, root, path):
            self.root = root
            self.path = path
            self.uuid = "uuid-123"
            self.matches = True
            self.market = {"FR": 1.0}
            self.material_kwargs = {"mass": 1.0}

        def get_ref_flow(self):
            pass

        def get_hs_class(self):
            pass

        def get_market(self):
            pass

        def get_matches(self):
            pass

    monkeypatch.setattr(pl, "IlcdProcess", FakeIlcd, raising=True)

    # pipeline returns the final weighted averages
    monkeypatch.setattr(
        pl, "epd_pipeline", lambda process, epd_path: {"GWP": 3.5}, raising=True
    )

    out = pl.run_materia(prod_dir, epd_dir)
    assert out == ({"GWP": 3.5}, "uuid-123")
