from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

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
from materia.core.constants import MASS_KWARGS


def gen_xml_objects(folder_path):
    if folder_path.is_file():
        folder = Path(folder_path).parent
    elif folder_path.is_dir():
        folder = Path(folder_path)
    else:
        raise ValueError("Not a file/folder path")

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
    epds = gen_epds(path_to_epd_folder)

    filters = []
    if process.matches:
        filters.append(UUIDFilter(process.matches))
    if process.material_kwargs:
        filters.append(UnitConformityFilter(process.material_kwargs))

    filtered_epds = list(gen_filtered_epds(epds, filters))

    if len(filtered_epds) == 0:
        print(f"{process.uuid}: switching to mass-based functional unit")
        process.material_kwargs = MASS_KWARGS
        filters = [f for f in filters if not isinstance(f, UnitConformityFilter)]
        filters.append(UnitConformityFilter(process.material_kwargs))
        epds = gen_epds(path_to_epd_folder)
        filtered_epds = list(gen_filtered_epds(epds, filters))

    if len(filtered_epds) == 0:
        return None, None

    for epd in filtered_epds:
        epd.get_lcia_results()

    avg_properties = average_material_properties(filtered_epds)
    mat = Material(**avg_properties)
    mat.rescale(process.material_kwargs)
    avg_properties = mat.to_dict()

    market_epds = {
        country: list(gen_locfiltered_epds(filtered_epds, [LocationFilter({country})]))
        for country in process.market
    }

    market_impacts = {
        country: average_impacts([epd.lcia_results for epd in epds])
        for country, epds in market_epds.items()
    }

    avg_gwps = weighted_averages(process.market, market_impacts)

    return avg_properties, avg_gwps


def run_materia(path_to_gen_folder: Path, path_to_epd_folder: Path, output_path: Path):
    for path, root in gen_xml_objects(path_to_gen_folder / "processes"):
        process = IlcdProcess(root=root, path=path)
        process.get_ref_flow()
        process.get_hs_class()
        process.get_market()
        process.get_matches()
        if process.matches:
            print(f"{process.uuid}: processing")
            avg_properties, avg_gwps = epd_pipeline(
                process, path_to_epd_folder / "processes"
            )
            if avg_properties is None and avg_gwps is None:
                print(f"{process.uuid}: cannot be completed\n")
            else:
                process.material = Material(**avg_properties)
                process.write_process(avg_gwps, output_path)
                print(f"{process.uuid}: completed\n")
