import materia.resources as resources
from importlib.resources import files


def test_regions_mapping_file_exists():
    assert files("materia").joinpath("data", "regions_mapping.json").exists()


def test_get_regions_mapping_returns_expected_keys():
    resources.get_regions_mapping.cache_clear()
    mapping = resources.get_regions_mapping()
    assert mapping["OCE"]["Regions"] == "Oceania"
    assert mapping["AFR"]["Regions"] == "Africa"
    assert mapping["RER"]["Regions"] == "Europe"


def test_get_regions_mapping_is_cached(monkeypatch):
    resources.get_regions_mapping.cache_clear()
    from materia.io import files as io_files

    calls = {"n": 0}

    def spy(path):
        calls["n"] += 1
        return {"dummy": True}

    monkeypatch.setattr(io_files, "read_json_file", spy)
    resources.get_regions_mapping()
    resources.get_regions_mapping()
    assert calls["n"] == 1


def test_get_regions_mapping_raises_on_invalid(monkeypatch):
    resources.get_regions_mapping.cache_clear()
    from materia.io import files as io_files

    monkeypatch.setattr(io_files, "read_json_file", lambda _: None)
    try:
        resources.get_regions_mapping()
    except ValueError:
        assert True
    else:
        assert False, "Expected ValueError"
