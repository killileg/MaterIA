# tests/unit/test_io_files_min.py
from materia.io import files as mod
import xml.etree.ElementTree as ET  # <-- add this import


def test_io_files_full_coverage(tmp_path):
    # ---- read_json_file ----
    # missing -> None
    assert mod.read_json_file(tmp_path / "missing.json") is None
    # invalid JSON -> None
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json}", encoding="utf-8")
    assert mod.read_json_file(bad_json) is None
    # valid JSON -> dict
    good_json = tmp_path / "good.json"
    good_json.write_text('{"a": 1}', encoding="utf-8")
    assert mod.read_json_file(good_json) == {"a": 1}

    # ---- write_json_file ----
    # success -> True
    out_json = tmp_path / "out.json"
    assert mod.write_json_file(out_json, {"x": [1, 2]}) is True
    assert mod.read_json_file(out_json) == {"x": [1, 2]}
    # failure (unserializable type) -> False
    assert mod.write_json_file(tmp_path / "bad_out.json", {"s": {1, 2}}) is False

    # ---- read_xml_root ----
    # missing -> None
    assert mod.read_xml_root(tmp_path / "missing.xml") is None
    # invalid XML -> None
    bad_xml = tmp_path / "bad.xml"
    bad_xml.write_text("<a>", encoding="utf-8")
    assert mod.read_xml_root(bad_xml) is None
    # valid XML -> root element
    good_xml = tmp_path / "good.xml"
    good_xml.write_text("<root><c/></root>", encoding="utf-8")
    root = mod.read_xml_root(good_xml)
    assert root.tag == "root"

    # ---- write_xml_root ----
    # success -> True and file is parseable
    out_xml = tmp_path / "out_dir" / "ok.xml"
    ok_root = ET.Element("r")
    assert mod.write_xml_root(ok_root, out_xml) is True
    assert out_xml.exists()
    parsed = ET.parse(out_xml).getroot()
    assert parsed.tag == "r"

    # failure -> False (attempt to write under a path that is a file, not a directory)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")  # create a file
    impossible = blocker / "child.xml"  # looks like a dir, but parent is a file
    bad_root = ET.Element("x")
    assert mod.write_xml_root(bad_root, impossible) is False

    # ---- gen_json_objects ----
    folder = tmp_path / "jsons"
    folder.mkdir()
    (folder / "ok.json").write_text('{"ok": true}', encoding="utf-8")
    (folder / "bad.json").write_text("oops", encoding="utf-8")
    (folder / "note.txt").write_text("{}", encoding="utf-8")
    json_items = list(mod.gen_json_objects(folder))
    assert [(p.name, d) for p, d in json_items] == [("ok.json", {"ok": True})]

    # ---- gen_xml_objects ----
    (folder / "a.xml").write_text("<a/>", encoding="utf-8")
    (folder / "b.xml").write_text("<b>", encoding="utf-8")
    (folder / "c.txt").write_text("<c/>", encoding="utf-8")
    xml_items = list(mod.gen_xml_objects(folder))
    assert [(p.name, r.tag) for p, r in xml_items] == [("a.xml", "a")]
