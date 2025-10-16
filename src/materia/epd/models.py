from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from materia.core.constants import (
    FLOW_PROPERTY_MAPPING,
    UNIT_QUANTITY_MAPPING,
    UNIT_PROPERTY_MAPPING,
    INDICATOR_SYNONYMS,
    ATTR,
    XP,
    NS,
    FLOW_NS,
    EPD_NS,
)
from materia.io.paths import MARKET_FOLDER, MATCHES_FOLDER
from materia.core.utils import to_float
from materia.io.files import read_json_file
from materia.geo.locations import ilcd_to_iso_location
from materia.core.physics import Material
from materia.metrics.normalize import normalize_module_values


class IlcdFlow:
    root: ET.Element

    def __post_init__(self):
        self._get_units()
        self._get_props()

    def _get_units(self):
        self.units = []
        for prop in self.root.findall(XP.FLOW_PROPERTY, FLOW_NS):
            mean_value = prop.findtext(XP.MEAN_VALUE, namespaces=FLOW_NS)
            ref = prop.find(XP.REF_TO_FLOW_PROP, FLOW_NS)

            if mean_value and ref is not None:
                amount = mean_value
                uuid = ref.attrib.get(ATTR.REF_OBJECT_ID)
                name = next(
                    (
                        desc.text
                        for desc in ref.findall(XP.SHORT_DESC, FLOW_NS)
                        if desc.attrib.get(ATTR.LANG) == "en"
                    ),
                    None,
                )
                unit = next(
                    (
                        symbol
                        for symbol, mapped_uuid in FLOW_PROPERTY_MAPPING.items()
                        if mapped_uuid == uuid
                    ),
                    None,
                )

                self.units.append(
                    {
                        "Name": name,
                        "Unit": unit,
                        "Amount": to_float(amount, positive=True),
                    }
                )

    def _get_props(self):
        self.props = []
        matml = self.root.find(XP.MATML_DOC, FLOW_NS)

        if matml is None:
            return

        amounts = {
            pd.attrib.get(ATTR.PROPERTY): pd.findtext(XP.PROP_DATA, namespaces=FLOW_NS)
            for pd in matml.findall(XP.PROPERTY_DATA, FLOW_NS)
            if pd.attrib.get(ATTR.PROPERTY)
            and pd.find(XP.PROP_DATA, FLOW_NS) is not None
        }

        for detail in matml.findall(XP.PROPERTY_DETAILS, FLOW_NS):
            prop_id = detail.attrib.get(ATTR.ID)
            name = detail.findtext(XP.PROP_NAME, namespaces=FLOW_NS)
            unit = detail.find(XP.PROP_UNITS, FLOW_NS)
            unit_name = unit.attrib.get(ATTR.NAME) if unit is not None else None
            amount = amounts.get(prop_id)

            if name and unit_name and amount is not None:
                self.props.append(
                    {
                        "Name": name,
                        "Unit": unit_name,
                        "Amount": to_float(amount, positive=True),
                    }
                )


@dataclass
class IlcdProcess:
    root: ET.Element
    path: Path

    def __post_init__(self):
        self._get_uuid()
        self._get_loc()

    def _get_uuid(self) -> str | None:
        node = self.root.find(XP.UUID, NS)
        self.uuid = node.text.strip() if (node is not None and node.text) else None

    def _get_loc(self) -> str | None:
        loc_node = self.root.find(XP.LOCATION, NS)
        loc_code = loc_node.attrib.get(ATTR.LOCATION) if loc_node is not None else None
        self.loc = ilcd_to_iso_location(loc_code) if loc_code else None

    def get_ref_flow(self) -> IlcdFlow:
        ref_flow_id = self.root.findtext(XP.QUANT_REF, namespaces=NS).strip()
        ref_flow_exchange = self.root.find(XP.exchange_by_id(ref_flow_id), NS)
        ref_flow_uuid = ref_flow_exchange.find(XP.REF_TO_FLOW, NS).attrib.get(
            ATTR.REF_OBJECT_ID
        )

        flows_folder = self.path.parent.parent / "flows"
        flow_file = flows_folder / f"{ref_flow_uuid}.xml"
        self.ref_flow = IlcdFlow(root=ET.parse(flow_file).getroot())

        exchange_amount = to_float(
            ref_flow_exchange.findtext(XP.MEAN_AMOUNT, namespaces=NS), positive=True
        )
        kwargs = {
            v: None
            for v in set(UNIT_QUANTITY_MAPPING.values())
            | set(UNIT_PROPERTY_MAPPING.values())
        }

        for u in self.ref_flow.units:
            field = UNIT_QUANTITY_MAPPING.get(u.get("Unit"))
            if field and isinstance(u.get("Amount"), (int, float)):
                kwargs[field] = u["Amount"] * exchange_amount

        for p in self.ref_flow.props:
            field = UNIT_PROPERTY_MAPPING.get(p.get("Unit"))
            if field and isinstance(p.get("Amount"), (int, float)):
                kwargs[field] = p["Amount"]

        self.material_kwargs = kwargs
        self.material = Material(**kwargs)

    def get_lcia_results(self) -> list[dict]:
        results = []

        for lcia_result in self.root.findall(XP.LCIA_RESULT, EPD_NS):
            ref_method = lcia_result.find(XP.REF_TO_LCIA_METHOD, EPD_NS)
            name = "Unknown"

            if ref_method is not None:
                for sd in ref_method.findall(XP.SHORT_DESC, EPD_NS):
                    if sd.attrib.get(ATTR.LANG) == "en":
                        name = sd.text.strip() if sd.text else "Unknown"
                        break

            amount_elems = lcia_result.findall(XP.AMOUNT, EPD_NS)
            values = normalize_module_values(
                amount_elems, scaling_factor=self.material.scaling_factor
            )

            canon = next(
                (c for c, aliases in INDICATOR_SYNONYMS.items() if name in aliases),
                None,
            )
            if canon:
                results.append({"name": canon, "values": values})

        self.lcia_results = results

    def get_hs_class(self) -> str:
        hs_node = self.root.find(XP.HS_CLASSIFICATION, NS)
        top_class = hs_node.find(XP.CLASS_LEVEL_2, NS)
        self.hs_class = top_class.attrib.get(ATTR.CLASS_ID)

    def get_market(self) -> dict:
        market_path = os.path.join(MARKET_FOLDER, f"{self.hs_class}.json")
        self.market = read_json_file(market_path)

    def get_matches(self) -> dict:
        matches_path = os.path.join(MATCHES_FOLDER, f"{self.uuid}.json")
        self.matches = read_json_file(matches_path)
