from contextlib import contextmanager
from pathlib import Path

import materia.resources as res


def test_resources_full_coverage(tmp_path):
    # ---- reset caches (important for deterministic tests) ----
    res.load_json_from_package.cache_clear()
    res.get_regions_mapping.cache_clear()
    res.get_indicator_synonyms.cache_clear()
    res.get_market_shares.cache_clear()
    res.get_location_data.cache_clear()

    # ---- patch paths & importlib.resources facades ----
    pkg_root = tmp_path / "pkg"  # pretend package root; no real files needed
    pkg_root.mkdir()
    res.USER_DATA_DIR = tmp_path / "user"
    res.USER_DATA_DIR.mkdir()

    def files(_pkg):  # returns a base Path that supports .joinpath(...)
        return pkg_root

    @contextmanager
    def as_file(pathlike):
        # mimic importlib.resources.as_file context manager
        yield Path(pathlike)

    res.files = files
    res.as_file = as_file

    # ---- stub materia.io.files API used by the module ----
    calls = []

    def read_json_file(path):
        p = Path(path)
        # return concrete data for known names; None for others to trigger errors
        if p.name == "regions_mapping.json":
            return {"regions": True}
        if p.name == "indicator_synonyms.json":
            return {"synonyms": True}
        if p.parent.name == "locations" and p.name == "FR.json":
            return {"FR": {"ok": 1}}
        if p.name == "7208.json":
            return {"share": 1}
        if p.name == "fallback.json":
            return {"fb": 1}
        return None  # triggers ValueError branches

    def gen_json_objects(folder_path):
        # yield at least one (filename, data) pair
        yield ("a.json", {"A": 1})

    def write_json_file(path, data):
        calls.append((Path(path), data))

    res.io_files.read_json_file = read_json_file
    res.io_files.gen_json_objects = gen_json_objects
    res.io_files.write_json_file = write_json_file

    # ---- get_data_file: user path branch ----
    user_file = res.USER_DATA_DIR / "market_shares" / "exists.json"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text("{}", encoding="utf-8")
    assert res.get_data_file("exists.json", "market_shares") == user_file

    # ---- get_data_file: fallback to package branch ----
    # (no file created; as_file just returns the joined path)
    fb = res.get_data_file("fallback.json")
    assert fb == pkg_root / "data" / "fallback.json"

    # ---- load_json_from_package: success ----
    assert res.load_json_from_package("regions_mapping.json") == {"regions": True}

    # ---- load_json_from_package: failure -> ValueError ----
    import pytest

    with pytest.raises(ValueError):
        res.load_json_from_package("missing.json")

    # ---- iter_json_from_package_folder ----
    items = list(res.iter_json_from_package_folder("any_folder"))
    assert items == [("a.json", {"A": 1})]

    # ---- get_regions_mapping / get_indicator_synonyms (cached wrappers) ----
    assert res.get_regions_mapping() == {"regions": True}
    assert res.get_indicator_synonyms() == {"synonyms": True}

    # ---- get_market_shares: success via user or package path ----
    assert res.get_market_shares("7208") == {"share": 1}

    # ---- get_market_shares: failure when data is None ----
    res.get_market_shares.cache_clear()
    with pytest.raises(ValueError):
        res.get_market_shares("0000")

    # ---- get_location_data (locations/FR.json) ----
    assert res.get_location_data("FR") == {"FR": {"ok": 1}}

    # ---- update_user_data writes to USER_DATA_DIR/subfolder/filename ----
    res.update_user_data("custom", "x.json", {"k": 2})
    target = res.USER_DATA_DIR / "custom" / "x.json"
    assert calls and calls[-1][0] == target and calls[-1][1] == {"k": 2}
    assert target.parent.exists()
