# test_models_full_coverage.py
import xml.etree.ElementTree as ET
from pathlib import Path
from materia_epd.epd import models


def test_models_full_coverage(tmp_path):
    # -------- Patch minimal constants & helpers (no namespaces) --------
    models.FLOW_PROPERTY_MAPPING = {"kg": "UUID-MASS"}
    models.UNIT_QUANTITY_MAPPING = {"kg": "mass"}
    models.UNIT_PROPERTY_MAPPING = {"g/cm3": "gross_density"}
    models.NS = {}

    class XP:
        FLOW_PROPERTY = "flowProperty"
        MEAN_VALUE = "meanValue"
        REF_TO_FLOW_PROP = "refToFlowProp"
        SHORT_DESC = "shortDescription"
        MATML_DOC = "matML_Doc"
        PROPERTY_DATA = "propertyData"
        PROP_DATA = "propData"
        PROPERTY_DETAILS = "propertyDetails"
        PROP_NAME = "propName"
        PROP_UNITS = "propUnits"

        UUID = "UUID"
        LOCATION = "location"
        QUANT_REF = "quantitativeReference"
        REF_TO_FLOW = "refToFlow"
        MEAN_AMOUNT = "meanAmount"
        LCIA_RESULT = ".//lciaResult"
        REF_TO_LCIA_METHOD = "refToLCIAMethod"
        AMOUNT = "amount"
        HS_CLASSIFICATION = ".//hsClassification"
        CLASS_LEVEL_2 = "classLevel2"

        @staticmethod
        def exchange_by_id(_id: str) -> str:
            return f".//exchange[@id='{_id}']"

    class ATTR:
        REF_OBJECT_ID = "refObjectId"
        LANG = "lang"
        LOCATION = "location"
        PROPERTY = "property"
        ID = "id"
        NAME = "name"
        CLASS_ID = "classId"

    models.XP = XP
    models.ATTR = ATTR

    models.to_float = lambda v, positive=False: float(v)
    models.ilcd_to_iso_location = lambda code: code

    class Material:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.scaling_factor = 2.0

    models.Material = Material
    models.normalize_module_values = lambda elems, scaling_factor=1.0: [10, 20, 30]
    models.get_indicator_synonyms = lambda: {"GWP": ["Global Warming Potential"]}
    models.get_market_shares = lambda _loc, _hs: {"EU": 0.7}
    models.read_json_file = lambda _p: {"match": True}
    models.MATCHES_FOLDER = str(tmp_path)

    def _ilcdflow_init(self, root):
        self.root = root
        self._get_units()
        self._get_props()

    models.IlcdFlow.__init__ = _ilcdflow_init

    # -------- Tiny on-disk dataset --------
    base = tmp_path / "dataset"
    flows_dir = base / "flows"
    processes_dir = base / "processes"
    flows_dir.mkdir(parents=True, exist_ok=True)
    processes_dir.mkdir(parents=True, exist_ok=True)

    flow_xml = """<flow>
      <flowProperty>
        <meanValue>2.0</meanValue>
        <refToFlowProp refObjectId="UUID-MASS">
          <shortDescription lang="en">Mass</shortDescription>
        </refToFlowProp>
      </flowProperty>
      <matML_Doc>
        <propertyDetails id="PD1">
          <propName>Density</propName>
          <propUnits name="g/cm3" />
        </propertyDetails>
        <propertyData property="PD1">
          <propData>7.8</propData>
        </propertyData>
      </matML_Doc>
    </flow>"""
    (flows_dir / "FLOW-UUID-1.xml").write_text(flow_xml, encoding="utf-8")

    process_xml = """<process>
      <UUID>abc-123</UUID>
      <location location="FR" />
      <quantitativeReference>ex1</quantitativeReference>
      <exchanges>
        <exchange id="ex1">
          <meanAmount>3</meanAmount>
          <refToFlow refObjectId="FLOW-UUID-1" />
        </exchange>
      </exchanges>
      <lciaResults>
        <lciaResult>
          <refToLCIAMethod>
            <shortDescription lang="en">Global Warming Potential</shortDescription>
          </refToLCIAMethod>
          <amount>1</amount><amount>2</amount><amount>3</amount>
        </lciaResult>
      </lciaResults>
      <hsClassification>
        <classLevel2 classId="72"/>
      </hsClassification>
    </process>"""
    process_path = processes_dir / "proc.xml"
    process_path.write_text(process_xml, encoding="utf-8")

    # -------- Drive all code paths --------
    proc = models.IlcdProcess(root=ET.fromstring(process_xml), path=process_path)

    assert proc.uuid == "abc-123"
    assert proc.loc == "FR"

    proc.get_ref_flow()
    assert proc.material_kwargs["mass"] == 6.0
    assert proc.material_kwargs["gross_density"] == 7.8

    proc.get_lcia_results()
    assert proc.lcia_results == [{"name": "GWP", "values": [10, 20, 30]}]

    proc.get_hs_class()
    assert proc.hs_class == "72"
    assert proc.get_market() == {"EU": 0.7}

    proc.get_matches()
    assert proc.matches == {"match": True}

    f_no_matml = models.IlcdFlow.__new__(models.IlcdFlow)
    f_no_matml.root = ET.fromstring("<flow/>")
    f_no_matml._get_props()

    f_with_matml = models.IlcdFlow.__new__(models.IlcdFlow)
    f_with_matml.root = ET.fromstring(flow_xml)
    f_with_matml.__post_init__()
    assert f_with_matml.units and f_with_matml.props


def test_write_process_updates_amounts_and_uses_output_path(monkeypatch, tmp_path):
    process_xml = """<process>
      <UUID>abc-123</UUID>
      <lciaResults>
        <lciaResult>
          <refToLCIAMethod>
            <shortDescription lang="en">Global Warming Potential</shortDescription>
          </refToLCIAMethod>
          <amount module="A1-A3">0</amount>
          <amount module="A4">0</amount>
          <amount module="C1">0</amount>
          <amount module="C2">0</amount>
          <amount module="C3">0</amount>
          <amount module="C4">0</amount>
          <amount module="D">0</amount>
        </lciaResult>
      </lciaResults>
    </process>"""
    root = ET.fromstring(process_xml)
    proc_path = tmp_path / "dataset" / "processes" / "proc.xml"
    proc_path.parent.mkdir(parents=True, exist_ok=True)
    proc_path.write_text(process_xml, encoding="utf-8")

    proc = models.IlcdProcess(root=root, path=proc_path)

    captured = {}

    def fake_write_xml_root(r, p):
        captured["root"] = r
        captured["path"] = Path(p)
        return True

    monkeypatch.setattr(models, "write_xml_root", fake_write_xml_root, raising=True)

    results = {
        "Global Warming Potential": {
            "A1-A3": 1108.0370876767083,
            "C1": 8.826807938835385,
            "C2": 8.825722954263789,
            "C3": 62.08764988382313,
            "C4": 56.859680185480855,
            "D": -98.9221132329585,
        }
    }

    out_dir = tmp_path / "out"
    ok = proc.write_process(results, out_dir)
    assert ok is True

    assert captured["path"] == out_dir / "processes" / "abc-123.xml"

    updated = {}
    for amt in captured["root"].findall(".//amount"):
        mod = amt.attrib.get("module")
        if mod:
            updated[mod] = amt.text

    assert updated["A1-A3"] == str(float(results["Global Warming Potential"]["A1-A3"]))
    assert updated["C1"] == str(float(results["Global Warming Potential"]["C1"]))
    assert updated["C2"] == str(float(results["Global Warming Potential"]["C2"]))
    assert updated["C3"] == str(float(results["Global Warming Potential"]["C3"]))
    assert updated["C4"] == str(float(results["Global Warming Potential"]["C4"]))
    assert updated["D"] == str(float(results["Global Warming Potential"]["D"]))
    assert updated["A4"] == "0"


def test_write_process_skips_missing_indicator_and_still_writes(monkeypatch, tmp_path):
    process_xml = """<process>
      <UUID>abc-123</UUID>
      <lciaResults>
        <lciaResult>
          <refToLCIAMethod>
            <shortDescription lang="en">Some Other Indicator</shortDescription>
          </refToLCIAMethod>
          <amount module="A1-A3">0</amount>
        </lciaResult>
      </lciaResults>
    </process>"""
    root = ET.fromstring(process_xml)
    proc = models.IlcdProcess(root=root, path=tmp_path / "dataset/processes/proc.xml")

    called = {}

    def fake_write_xml_root(r, p):
        called["path"] = Path(p)
        return True

    monkeypatch.setattr(models, "write_xml_root", fake_write_xml_root, raising=True)

    results = {"Global Warming Potential": {"A1-A3": 123.0}}

    ok = proc.write_process(results, tmp_path / "out")
    assert ok is True

    amt = root.find(".//amount[@module='A1-A3']")
    assert amt is not None and amt.text == "0"

    assert called["path"] == tmp_path / "out" / "processes" / "abc-123.xml"


def test_write_process_attr_lookup_returns_none_when_no_known_attr(
    monkeypatch, tmp_path
):
    process_xml = """<process>
      <UUID>abc-123</UUID>
      <lciaResults>
        <lciaResult>
          <refToLCIAMethod>
            <shortDescription lang="en">Global Warming Potential</shortDescription>
          </refToLCIAMethod>
          <amount someOtherAttr="X">0</amount>
          <amount anotherAttr="Y">0</amount>
        </lciaResult>
      </lciaResults>
    </process>"""
    root = ET.fromstring(process_xml)
    proc = models.IlcdProcess(root=root, path=tmp_path / "dataset/processes/proc.xml")

    monkeypatch.setattr(models, "write_xml_root", lambda r, p: True, raising=True)

    results = {"Global Warming Potential": {"A1-A3": 10.0, "C1": 20.0}}

    ok = proc.write_process(results, tmp_path / "out")
    assert ok is True

    amounts = root.findall(".//amount")
    assert [a.text for a in amounts] == ["0", "0"]
