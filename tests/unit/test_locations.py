# tests/unit/test_locations.py
import json
from pathlib import Path
import pytest

import materia.geo.locations as loc  # module under test
from materia.core.errors import LocationNotFoundError


def test_ilcd_to_iso_location_basic():
    # From hard-coded overrides in ilcd_to_iso_location
    assert loc.ilcd_to_iso_location("GLO") == "GLO"
    assert loc.ilcd_to_iso_location("UK") == "GBR"

    # From pycountry lookup (alpha-2 -> alpha-3)
    assert loc.ilcd_to_iso_location("FR") == "FRA"

    # From REGIONS_MAPPING ("EU-27" -> "Europe")
    assert loc.ilcd_to_iso_location("EU-27") == "Europe"


def test_get_location_attribute_and_missing(tmp_path: Path, monkeypatch):
    # Point the module's LOCATIONS_FOLDER to a temp folder
    monkeypatch.setattr(loc, "LOCATIONS_FOLDER", tmp_path)

    # Create a mock location file: LUX.json
    (tmp_path / "LUX.json").write_text(
        json.dumps({"Parent": "EU", "Children": ["LUX-1", "LUX-2"]}),
        encoding="utf-8",
    )

    # Reads existing attributes
    assert loc.get_location_attribute("LUX", "Parent") == "EU"
    assert loc.get_location_attribute("LUX", "Children") == ["LUX-1", "LUX-2"]

    # Missing file should raise
    with pytest.raises(LocationNotFoundError):
        loc.get_location_attribute("MISSING", "Parent")


def test_escalate_location_set(tmp_path: Path, monkeypatch):
    # Point the module's LOCATIONS_FOLDER to a temp folder
    monkeypatch.setattr(loc, "LOCATIONS_FOLDER", tmp_path)

    # LUX has parent EU; EU has a set of children -> escalate should return EU children
    (tmp_path / "LUX.json").write_text(json.dumps({"Parent": "EU"}), encoding="utf-8")
    (tmp_path / "EU.json").write_text(
        json.dumps({"Children": ["FRA", "DEU", "LUX"]}),
        encoding="utf-8",
    )

    out = loc.escalate_location_set({"LUX"})
    assert out == {"FRA", "DEU", "LUX"}
