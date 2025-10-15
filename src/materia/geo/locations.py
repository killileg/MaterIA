from pathlib import Path
import pycountry

from materia.io.files import read_json_file
from materia.io.paths import LOCATIONS_FOLDER
from materia.resources import get_regions_mapping
from materia.core.errors import LocationNotFoundError


def ilcd_to_iso_location(ilcd_code):
    """Convert an ILCD location code to an ISO-compliant location code."""
    return (
        {"GLO": "GLO", "UK": "GBR"}.get(ilcd_code)
        or (get_regions_mapping().get(ilcd_code) or {}).get("Regions")
        or getattr(pycountry.countries.get(alpha_2=ilcd_code), "alpha_3", None)
        or getattr(pycountry.historic_countries.get(alpha_2=ilcd_code), "alpha_3", None)
    )


def get_location_attribute(location_code: str, attribute: str):
    """Returns a specific attribute from a location JSON file."""
    loc_file = Path(LOCATIONS_FOLDER) / f"{location_code}.json"
    if not loc_file.exists():
        raise LocationNotFoundError(loc_file)
    return (read_json_file(loc_file) or {}).get(attribute)


def escalate_location_set(location_set):
    """Return all children of the parent locations of a given location set."""
    return {
        child
        for parent in {get_location_attribute(loc, "Parent") for loc in location_set}
        for child in (get_location_attribute(parent, "Children") or [])
    }
