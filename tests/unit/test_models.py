# tests/unit/test_models.py
from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import types
import pytest

from materia.epd import models as mdl  # under test


# ---------- helpers: simplify constants so we can craft tiny XMLs ----------
class _ATTR:
    REF_OBJECT_ID = "refObjectId"
    LANG = "lang"
    LOCATION = "location"
    PROPERTY = "property"
    ID = "id"
    NAME = "name"
    CLASS_ID = "classId"


class _XP:
    UUID = ".//uuid"
    LOCATION = ".//location"
    QUANT_REF = ".//quantRef"
    LCIA_RESULT = ".//lcia"
    REF_TO_LCIA_METHOD = ".//method"
    SHORT_DESC = ".//short"
    AMOUNT = ".//amount"
    HS_CLASSIFICATION = ".//hs"
    CLASS_LEVEL_2 = ".//class2"
    REF_TO_FLOW = ".//refToFlow"
    MEAN_AMOUNT = ".//meanAmount"

    @staticmethod
    def exchange_by_id(x: str) -> str:
        return f".//exchange[@id='{x}']"


# We’ll use empty namespace dicts in tests
@pytest.fixture(autouse=True)
def patch_constants(monkeypatch):
    # Patch constants the model expects
    monkeypatch.setattr(mdl, "ATTR", _ATTR, raising=True)
    monkeypatch.setattr(mdl, "XP", _XP, raising=True)
    monkeypatch.setattr(mdl, "NS", {}, raising=True)
    monkeypatch.setattr(mdl, "FLOW_NS", {}, raising=True)
    monkeypatch.setattr(mdl, "EPD_NS", {}, raising=True)

    # Minimal mappings used in get_ref_flow()
    monkeypatch.setattr(mdl, "FLOW_PROPERTY_MAPPING", {"kg": "uuid-mass"}, raising=True)
    monkeypatch.setattr(mdl, "UNIT_QUANTITY_MAPPING", {"kg": "mass"}, raising=True)
    monkeypatch.setattr(
        mdl, "UNIT_PROPERTY_MAPPING", {"kg/m3": "gross_density"}, raising=True
    )
    monkeypatch.setattr(
        mdl,
        "INDICATOR_SYNONYMS",
        {"GWP": {"GWP", "Global Warming Potential"}},
        raising=True,
    )


# ----------------------------- IlcdProcess: uuid + loc -----------------------------


def test_ilcdprocess_post_init_sets_uuid_and_loc(monkeypatch):
    root = ET.fromstring(
        "<process>" "  <uuid>abc-123</uuid>" '  <location location="FR"/>' "</process>"
    )
    monkeypatch.setattr(mdl, "ilcd_to_iso_location", lambda code: "FRA", raising=True)

    proc = mdl.IlcdProcess(root=root, path=Path("dummy.xml"))
    assert proc.uuid == "abc-123"
    assert proc.loc == "FRA"


# ----------------------------- get_ref_flow: material kwargs -----------------------


def test_get_ref_flow_builds_material_and_kwargs(tmp_path: Path, monkeypatch):
    # process file path structure: <tmp>/epd/proc.xml so flows live in <tmp>/flows
    epd_dir = tmp_path / "epd"
    flows_dir = tmp_path / "flows"
    epd_dir.mkdir()
    flows_dir.mkdir()

    # The referenced flow UUID, and exchange amount
    flow_uuid = "flow-001"
    exchange_id = "x1"

    # Process XML: refers to the flow via exchange
    proc_xml = ET.fromstring(
        "<process>"
        f"  <uuid>u-1</uuid>"
        '  <location location="FR"/>'
        f"  <quantRef>{exchange_id}</quantRef>"
        f'  <exchange id="{exchange_id}">'
        f'    <refToFlow { _ATTR.REF_OBJECT_ID }="{flow_uuid}"/>'
        f"    <meanAmount>3.0</meanAmount>"
        f"  </exchange>"
        "</process>"
    )
    proc_path = epd_dir / "proc.xml"
    ET.ElementTree(proc_xml).write(proc_path, encoding="utf-8")

    # A flows file must exist, but we’ll fake IlcdFlow to avoid complex XML
    (flows_dir / f"{flow_uuid}.xml").write_text("<flow/>", encoding="utf-8")

    created = {}

    class FakeIlcdFlow:
        def __init__(self, root):
            # 2 kg (unit) * 3.0 (exchange) -> mass = 6.0
            self.units = [{"Name": "Mass", "Unit": "kg", "Amount": 2.0}]
            # property goes through unchanged
            self.props = [{"Name": "Density", "Unit": "kg/m3", "Amount": 1000.0}]

    class FakeMaterial:
        def __init__(self, **kw):
            created["kwargs"] = kw
            self.scaling_factor = 1.0

    monkeypatch.setattr(mdl, "IlcdFlow", FakeIlcdFlow, raising=True)
    monkeypatch.setattr(mdl, "Material", FakeMaterial, raising=True)

    proc = mdl.IlcdProcess(root=proc_xml, path=proc_path)
    proc.get_ref_flow()

    # Expect kwargs mass = 2 * 3 and gross_density = 1000
    assert created["kwargs"]["mass"] == pytest.approx(6.0)
    assert created["kwargs"]["gross_density"] == pytest.approx(1000.0)
    assert isinstance(proc.material, FakeMaterial)


# ----------------------------- get_lcia_results ------------------------------------


def test_get_lcia_results_normalizes_and_canonizes(monkeypatch):
    # Build an LCIA structure with method name 'GWP' and two amount nodes
    root = ET.fromstring(
        "<process>"
        "  <lcia>"
        "    <method><short lang='en'>GWP</short></method>"
        "    <amount>1.0</amount>"
        "    <amount>2.0</amount>"
        "  </lcia>"
        "</process>"
    )

    proc = mdl.IlcdProcess(root=root, path=Path("dummy.xml"))

    # Fake Material so scaling_factor exists
    proc.material = types.SimpleNamespace(scaling_factor=1.0)

    # normalize_module_values returns a dict we can assert on
    monkeypatch.setattr(
        mdl,
        "normalize_module_values",
        lambda elems, scaling_factor: {"A1-A3": 3.0},
        raising=True,
    )

    proc.get_lcia_results()
    assert isinstance(proc.lcia_results, list)
    assert proc.lcia_results == [{"name": "GWP", "values": {"A1-A3": 3.0}}]


# ----------------------------- hs class + market/matches ---------------------------


def test_get_hs_class_and_market_and_matches(tmp_path: Path, monkeypatch):
    # XML with HS class level 2
    root = ET.fromstring("<process>" "  <hs><class2 classId='7208'/></hs>" "</process>")
    proc = mdl.IlcdProcess(root=root, path=Path("dummy.xml"))

    # Create small market/matches JSON files
    market_dir = tmp_path / "market"
    matches_dir = tmp_path / "matches"
    market_dir.mkdir()
    matches_dir.mkdir()
    (market_dir / "7208.json").write_text(
        json.dumps({"FR": 0.7, "DE": 0.3}), encoding="utf-8"
    )
    (matches_dir / "abc-uuid.json").write_text(
        json.dumps({"uuid": "abc-uuid"}), encoding="utf-8"
    )

    # Point folders in the module
    monkeypatch.setattr(mdl, "MARKET_FOLDER", str(market_dir), raising=True)
    monkeypatch.setattr(mdl, "MATCHES_FOLDER", str(matches_dir), raising=True)

    # Use a simple file reader
    def _reader(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    monkeypatch.setattr(mdl, "read_json_file", _reader, raising=True)

    # Execute
    proc.get_hs_class()
    assert proc.hs_class == "7208"

    proc.get_market()
    assert proc.market == {"FR": 0.7, "DE": 0.3}

    # pretend the process has uuid to fetch matches
    proc.uuid = "abc-uuid"
    proc.get_matches()
    assert proc.matches == {"uuid": "abc-uuid"}


def test_ilcdflow_parses_units_and_props(monkeypatch):
    """
    Covers IlcdFlow._get_units and _get_props happy paths:
    - unit mapping via FLOW_PROPERTY_MAPPING reverse lookup
    - english short description selection
    - props resolved via PROPERTY_DATA + PROPERTY_DETAILS
    """

    # Minimal constants used by IlcdFlow
    class ATTR:
        REF_OBJECT_ID = "refObjectId"
        LANG = "lang"
        PROPERTY = "property"
        ID = "id"
        NAME = "name"

    class XP:
        # units side
        FLOW_PROPERTY = ".//flowProp"
        MEAN_VALUE = ".//mean"
        REF_TO_FLOW_PROP = ".//ref"
        SHORT_DESC = ".//short"
        # props side
        MATML_DOC = ".//matml"
        PROPERTY_DATA = ".//propData"
        PROP_DATA = ".//value"
        PROPERTY_DETAILS = ".//propDetail"
        PROP_NAME = ".//name"
        PROP_UNITS = ".//units"

    # Patch the lookups IlcdFlow relies on
    monkeypatch.setattr(mdl, "ATTR", ATTR, raising=True)
    monkeypatch.setattr(mdl, "XP", XP, raising=True)
    monkeypatch.setattr(mdl, "FLOW_NS", {}, raising=True)

    # Reverse lookup: uuid -> "kg"
    monkeypatch.setattr(mdl, "FLOW_PROPERTY_MAPPING", {"kg": "uuid-mass"}, raising=True)

    # Build a tiny flow XML that matches the patched XPaths
    root = ET.fromstring(
        "<flow>"
        "  <flowProp>"
        "    <mean>2.0</mean>"
        "    <ref refObjectId='uuid-mass'>"
        "      <short lang='fr'>Masse</short>"
        "      <short lang='en'>Mass</short>"
        "    </ref>"
        "  </flowProp>"
        "  <matml>"
        "    <propData property='p1'><value>1000.0</value></propData>"
        "    <propDetail id='p1'>"
        "      <name>Density</name>"
        "      <units name='kg/m3'/>"
        "    </propDetail>"
        "  </matml>"
        "</flow>"
    )

    # Instantiate the real IlcdFlow; since it's not a dataclass, wire root manually
    flow = mdl.IlcdFlow()
    flow.root = root
    flow._get_units()
    flow._get_props()

    assert flow.units == [{"Name": "Mass", "Unit": "kg", "Amount": 2.0}]
    assert flow.props == [{"Name": "Density", "Unit": "kg/m3", "Amount": 1000.0}]


def test_ilcdflow_props_when_matml_missing(monkeypatch):
    """
    Covers the early-return branch in _get_props (matml is None).
    """

    class XP:
        MATML_DOC = ".//matml"  # won't be present
        # The rest are irrelevant for this test
        FLOW_PROPERTY = ".//flowProp"
        MEAN_VALUE = ".//mean"
        REF_TO_FLOW_PROP = ".//ref"
        SHORT_DESC = ".//short"
        PROPERTY_DATA = ".//propData"
        PROP_DATA = ".//value"
        PROPERTY_DETAILS = ".//propDetail"
        PROP_NAME = ".//name"
        PROP_UNITS = ".//units"

    monkeypatch.setattr(mdl, "XP", XP, raising=True)
    monkeypatch.setattr(mdl, "FLOW_NS", {}, raising=True)

    root = ET.fromstring("<flow/>")

    flow = mdl.IlcdFlow()
    flow.root = root
    flow._get_props()

    assert flow.props == []


def test_ilcdflow_post_init_calls_parsers(monkeypatch):
    """
    IlcdFlow has no __init__(root=...) in this codebase, so we instantiate it
    without args, set `root`, then call __post_init__ manually. We monkeypatch
    the two parser methods to confirm both lines (32–33) execute.
    """
    import xml.etree.ElementTree as ET
    from materia.epd import models as mdl

    # Minimal valid element; real parsing isn't needed for this coverage test.
    root = ET.fromstring("<flow/>")

    flow = mdl.IlcdFlow()
    flow.root = root

    calls = []

    def _stub_get_units(self):
        calls.append("units")

    def _stub_get_props(self):
        calls.append("props")

    # Patch the instance methods so we know they were invoked
    monkeypatch.setattr(mdl.IlcdFlow, "_get_units", _stub_get_units, raising=False)
    monkeypatch.setattr(mdl.IlcdFlow, "_get_props", _stub_get_props, raising=False)

    # Manually trigger the method that contains the two uncovered lines
    flow.__post_init__()

    assert calls == ["units", "props"]
