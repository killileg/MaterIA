# test_models_full_coverage.py
import xml.etree.ElementTree as ET
from materia.epd import models


def test_models_full_coverage(tmp_path):
    # -------- Patch minimal constants & helpers (no namespaces) --------
    models.FLOW_PROPERTY_MAPPING = {"kg": "UUID-MASS"}
    models.UNIT_QUANTITY_MAPPING = {"kg": "mass"}
    models.UNIT_PROPERTY_MAPPING = {"g/cm3": "density"}
    models.NS = {}
    models.FLOW_NS = {}
    models.EPD_NS = {}

    class XP:
        # Flow
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
        # Process
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

    # minimal stubs used internally
    models.to_float = lambda v, positive=False: float(v)
    models.ilcd_to_iso_location = lambda code: code

    class Material:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.scaling_factor = 2.0  # arbitrary but exercises scaling param flow

    models.Material = Material
    models.normalize_module_values = lambda elems, scaling_factor=1.0: [10, 20, 30]
    models.get_indicator_synonyms = lambda: {"GWP": ["Global Warming Potential"]}
    models.get_market_shares = lambda _hs: {"EU": 0.7}
    models.read_json_file = lambda _p: {"match": True}
    models.MATCHES_FOLDER = str(tmp_path)

    # Make IlcdFlow constructible as IlcdFlow(root=...)
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

    # Flow referenced by the process (has units + props)
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

    # Process using that flow + LCIA + HS classification
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

    # __post_init__: uuid + loc
    assert proc.uuid == "abc-123"
    assert proc.loc == "FR"

    # get_ref_flow: reads flow file, computes material kwargs
    proc.get_ref_flow()
    assert proc.material_kwargs["mass"] == 6.0  # 2.0 * 3
    assert proc.material_kwargs["density"] == 7.8  # from props

    # get_lcia_results: normalization + canonical name
    proc.get_lcia_results()
    assert proc.lcia_results == [{"name": "GWP", "values": [10, 20, 30]}]

    # get_hs_class + get_market
    proc.get_hs_class()
    assert proc.hs_class == "72"
    assert proc.get_market() == {"EU": 0.7}

    # get_matches (side-effect, not return)
    proc.get_matches()
    assert proc.matches == {"match": True}

    # Cover IlcdFlow.__post_init__ and _get_props early-return branch
    f_no_matml = models.IlcdFlow.__new__(models.IlcdFlow)
    f_no_matml.root = ET.fromstring("<flow/>")
    f_no_matml._get_props()  # triggers early 'return' branch

    f_with_matml = models.IlcdFlow.__new__(models.IlcdFlow)
    f_with_matml.root = ET.fromstring(flow_xml)
    f_with_matml.__post_init__()  # calls _get_units + _get_props
    assert f_with_matml.units and f_with_matml.props
