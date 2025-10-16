# tests/unit/test_files.py
from pathlib import Path
import json

from materia.io.files import (
    read_json_file,
    read_xml_root,
    gen_json_objects,
    gen_xml_objects,
)


# ---------- read_json_file ----------


def test_read_json_file_ok(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert read_json_file(p) == {"a": 1}


def test_read_json_file_invalid_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{ not: valid", encoding="utf-8")
    assert read_json_file(p) is None


def test_read_json_file_missing_returns_none(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert read_json_file(p) is None


# ---------- read_xml_root ----------


def test_read_xml_root_ok(tmp_path: Path):
    p = tmp_path / "ok.xml"
    p.write_text("<root><x/></root>", encoding="utf-8")
    root = read_xml_root(p)
    assert root is not None
    assert root.tag == "root"
    assert [child.tag for child in root] == ["x"]


def test_read_xml_root_invalid_returns_none(tmp_path: Path):
    p = tmp_path / "bad.xml"
    p.write_text("<root>", encoding="utf-8")  # parse error
    assert read_xml_root(p) is None


def test_read_xml_root_missing_returns_none(tmp_path: Path):
    p = tmp_path / "missing.xml"
    assert read_xml_root(p) is None


# ---------- gen_json_objects ----------


def test_gen_json_objects_filters_invalid_and_non_json(tmp_path: Path):
    (tmp_path / "a.json").write_text('{"ok": true}', encoding="utf-8")
    (tmp_path / "b.json").write_text("{ nope", encoding="utf-8")  # invalid
    (tmp_path / "c.txt").write_text("ignore me", encoding="utf-8")  # not .json

    out = list(gen_json_objects(tmp_path))
    assert [p.name for p, _ in out] == ["a.json"]
    assert out[0][1] == {"ok": True}


def test_gen_json_objects_empty_dir_yields_nothing(tmp_path: Path):
    assert list(gen_json_objects(tmp_path)) == []


# ---------- gen_xml_objects ----------


def test_gen_xml_objects_filters_invalid_and_non_xml(tmp_path: Path):
    (tmp_path / "a.xml").write_text("<root/>", encoding="utf-8")
    (tmp_path / "b.xml").write_text("<root>", encoding="utf-8")  # invalid
    (tmp_path / "c.txt").write_text("ignore me", encoding="utf-8")  # not .xml

    out = list(gen_xml_objects(tmp_path))
    assert [p.name for p, _ in out] == ["a.xml"]
    assert out[0][1].tag == "root"


def test_gen_xml_objects_empty_dir_yields_nothing(tmp_path: Path):
    assert list(gen_xml_objects(tmp_path)) == []
