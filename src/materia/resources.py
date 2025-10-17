# src/materia/resources.py
from __future__ import annotations

from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path

from materia.io import files as io_files
from materia.io.paths import USER_DATA_DIR


def get_data_file(filename: str, subfolder: str = "") -> Path:
    """Return path to user data if it exists, else fallback to package data."""
    user_file = USER_DATA_DIR / subfolder / filename
    if user_file.exists():
        return user_file

    resource = files(__package__).joinpath("data", subfolder, filename)
    with as_file(resource) as path:
        return path


@lru_cache(maxsize=None)
def load_json_from_package(*path_parts):
    """Load and cache a JSON file from the package data folder."""
    resource = files(__package__).joinpath("data", *path_parts)
    with as_file(resource) as path:
        data = io_files.read_json_file(path)
    if data is None:
        raise ValueError(f"Invalid or missing JSON file: {'/'.join(path_parts)}")
    return data


def iter_json_from_package_folder(*folder_parts: str):
    """Yield (filename, data) from all JSON files in a package folder."""
    folder = files(__package__).joinpath("data", *folder_parts)
    with as_file(folder) as folder_path:
        yield from io_files.gen_json_objects(folder_path)


@lru_cache(maxsize=1)
def get_regions_mapping():
    return load_json_from_package("regions_mapping.json")


@lru_cache(maxsize=1)
def get_indicator_synonyms():
    return load_json_from_package("indicator_synonyms.json")


@lru_cache(maxsize=1)
def get_market_shares(hs_code: str):
    """Load market share data for a given HS code, preferring user data."""
    path = get_data_file(f"{hs_code}.json", subfolder="market_shares")
    data = io_files.read_json_file(path)
    if data is None:
        raise ValueError(f"Invalid or missing market share data for HS code {hs_code}")
    return data


@lru_cache(maxsize=1)
def get_location_data(location_code: str):
    """Lazily load and cache location data for a given location code."""
    return load_json_from_package("locations", f"{location_code}.json")


def update_user_data(subfolder: str, filename: str, data: dict) -> None:
    """Save user-updated data to the ~/.materia/data folder."""
    target_dir = USER_DATA_DIR / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    io_files.write_json_file(target_file, data)
