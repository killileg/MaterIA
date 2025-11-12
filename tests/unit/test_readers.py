# tests/test_readers.py
import json

from materia_epd.io.files import (
    gen_json_objects,
    gen_xml_objects,
)


def test_gen_json_objects(tmp_path):
    (tmp_path / "ok.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{ nope", encoding="utf-8")
    files = list(gen_json_objects(tmp_path))
    assert len(files) == 1
    assert files[0][1] == {"ok": True}


def test_gen_xml_roots(tmp_path):
    (tmp_path / "ok.xml").write_text("<root/>", encoding="utf-8")
    (tmp_path / "bad.xml").write_text("<root>", encoding="utf-8")
    files = list(gen_xml_objects(tmp_path))
    assert len(files) == 1
    assert files[0][1].tag == "root"
