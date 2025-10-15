# src/materia/resources.py
from __future__ import annotations

from functools import lru_cache
from importlib.resources import as_file, files
from typing import Any, Mapping

from .io import files as io_files


@lru_cache(maxsize=1)
def get_regions_mapping() -> Mapping[str, Any]:
    """Lazily load and cache the regions mapping from package data."""
    resource = files(__package__).joinpath("data", "regions_mapping.json")

    with as_file(resource) as path:
        data = io_files.read_json_file(path)

    if data is None:
        raise ValueError("materia/data/regions_mapping.json is missing or invalid JSON")

    return data
