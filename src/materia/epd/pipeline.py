from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from pprint import pprint

from materia.epd.models import IlcdProcess
from materia.epd.filters import UUIDFilter, UnitConformityFilter, LocationFilter
from materia.geo.locations import escalate_location_set
from materia.metrics.averaging import (
    average_impacts,
    weighted_averages,
    average_material_properties,
)
from materia.core.physics import Material
from materia.core.errors import NoMatchingEPDError


def gen_xml_objects(folder_path):
    folder = Path(folder_path)
    for xml_file in folder.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            yield xml_file, root
        except Exception as e:
            print(f"❌ Error reading {xml_file.name}: {e}")


def gen_epds(folder_path):
    for path, root in gen_xml_objects(folder_path):
        yield IlcdProcess(root=root, path=path)


def gen_filtered_epds(epds, filters):
    for epd in epds:
        if all(filt.matches(epd) for filt in filters):
            yield epd


def gen_locfiltered_epds(epd_roots, filters, max_attempts=4):
    filters = [f for f in filters if isinstance(f, LocationFilter)]
    wanted_locations = set()
    for filt in filters:
        wanted_locations.update(filt.locations)
    for _ in range(max_attempts):
        epds = list(gen_filtered_epds(epd_roots, filters))
        if epds:
            yield from epds
            return
        wanted_locations = escalate_location_set(wanted_locations)
        filters = [LocationFilter(wanted_locations)]
    raise NoMatchingEPDError(filters)


def epd_pipeline(process: IlcdProcess, path_to_epd_folder: Path):
    EPD_FOLDER = Path(path_to_epd_folder) / "processes"

    epds = gen_epds(EPD_FOLDER)

    filters = []
    if process.matches:
        filters.append(UUIDFilter(process.matches))
    if process.material_kwargs:
        filters.append(UnitConformityFilter(process.material_kwargs))

    filtered_epds = list(gen_filtered_epds(epds, filters))
    for epd in filtered_epds:
        epd.get_lcia_results()

    avg_material = average_material_properties(filtered_epds)
    mat = Material(**avg_material)
    mat.rescale(process.material_kwargs)
    avg_material = mat.to_dict()
    pprint(avg_material)

    market_epds = {
        country: list(gen_locfiltered_epds(filtered_epds, [LocationFilter({country})]))
        for country in process.market
    }

    market_impacts = {
        country: average_impacts([epd.lcia_results for epd in epds])
        for country, epds in market_epds.items()
    }

    return weighted_averages(process.market, market_impacts)


def run_materia(path_to_gen_folder: Path, path_to_epd_folder: Path):
    GEN_PRODUCTS_FOLDER = Path(path_to_gen_folder)  # path to GenPro + "generic"
    for path, root in gen_xml_objects(GEN_PRODUCTS_FOLDER):  # GEN_PRODUCTS_FOLDER
        process = IlcdProcess(root=root, path=path)
        process.get_ref_flow()
        process.get_hs_class()
        process.get_market()
        process.get_matches()
        if process.matches:
            weighted = epd_pipeline(process, path_to_epd_folder)
            return weighted, process.uuid
