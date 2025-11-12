# tests/unit/test_files.py
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from materia_epd.io import files as mod


# ---------- helpers ----------
def _touch_with_time(p: Path, t: float, content="<r/>"):
    p.write_text(content, encoding="utf-8")
    os.utime(p, (t, t))


# ---------- JSON ----------
def test_read_json_file_ok_and_failures(tmp_path):
    # missing -> None (FileNotFoundError branch)
    assert mod.read_json_file(tmp_path / "missing.json") is None

    # invalid JSON -> None (JSONDecodeError branch)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json}", encoding="utf-8")
    assert mod.read_json_file(bad) is None

    # valid JSON -> dict
    good = tmp_path / "good.json"
    good.write_text('{"a":[1,2]}', encoding="utf-8")
    assert mod.read_json_file(good) == {"a": [1, 2]}


def test_write_json_file_ok_and_unserializable(tmp_path):
    out = tmp_path / "out.json"
    assert mod.write_json_file(out, {"x": 1}) is True
    assert mod.read_json_file(out) == {"x": 1}

    # unserializable -> False (TypeError/ValueError branch)
    assert mod.write_json_file(tmp_path / "bad_out.json", {"s": {1, 2}}) is False


# ---------- XML ----------
def test_read_xml_root_ok_and_failures(tmp_path):
    # missing -> None (FileNotFoundError)
    assert mod.read_xml_root(tmp_path / "missing.xml") is None

    # malformed -> None (ET.ParseError)
    bad = tmp_path / "bad.xml"
    bad.write_text("<root>", encoding="utf-8")
    assert mod.read_xml_root(bad) is None

    # valid -> Element
    good = tmp_path / "good.xml"
    good.write_text("<r/>", encoding="utf-8")
    root = mod.read_xml_root(good)
    assert root is not None and root.tag == "r"


def test_write_xml_root_ok_and_failure(tmp_path):
    # ok path
    out = tmp_path / "sub" / "ok.xml"
    assert mod.write_xml_root(ET.Element("r"), out) is True
    assert ET.parse(out).getroot().tag == "r"

    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    assert mod.write_xml_root(ET.Element("x"), blocker / "child.xml") is False


# ---------- generators ----------
def test_gen_json_objects_filters_only_valid_json(tmp_path):
    folder = tmp_path / "jsons"
    folder.mkdir()
    (folder / "ok.json").write_text('{"ok": true}', encoding="utf-8")
    (folder / "bad.json").write_text("oops", encoding="utf-8")
    (folder / "note.txt").write_text("{}", encoding="utf-8")

    items = list(mod.gen_json_objects(folder))
    assert [(p.name, d) for p, d in items] == [("ok.json", {"ok": True})]


def test_gen_xml_objects_filters_only_valid_xml(tmp_path):
    folder = tmp_path / "xmls"
    folder.mkdir()
    (folder / "a.xml").write_text("<a/>", encoding="utf-8")
    (folder / "b.xml").write_text("<b>", encoding="utf-8")  # invalid
    (folder / "c.txt").write_text("<c/>", encoding="utf-8")

    items = list(mod.gen_xml_objects(folder))
    assert [(p.name, r.tag) for p, r in items] == [("a.xml", "a")]


# ---------- latest_flow_file ----------
def test_latest_flow_file_raises_when_no_candidates(tmp_path):
    flows = tmp_path / "flows_empty"
    flows.mkdir()
    uuid = "nope-uuid"

    with pytest.raises(FileNotFoundError) as excinfo:
        mod.latest_flow_file(flows, uuid)

    assert f"uuid={uuid}" in str(excinfo.value)


def test_latest_flow_file_prefers_highest_version_over_mtime(tmp_path):
    flows = tmp_path / "flows_v"
    flows.mkdir()
    uuid = "abc-uuid"

    # mtime newest on the base (no version)
    base = flows / f"{uuid}.xml"
    _touch_with_time(base, time.time() + 500)

    # older versioned files present
    v10 = flows / f"{uuid}_version1.0.xml"
    v21 = flows / f"{uuid}_version2.1.xml"
    _touch_with_time(v10, time.time() - 100)
    _touch_with_time(v21, time.time() - 200)

    chosen = mod.latest_flow_file(flows, uuid)
    assert chosen == v21  # exercises the return line with version-aware sort_key


def test_latest_flow_file_uses_mtime_when_no_versions(tmp_path):
    flows = tmp_path / "flows_mtime"
    flows.mkdir()
    uuid = "zzz-uuid"

    older = flows / f"{uuid}.xml"
    newer = flows / f"{uuid}-copy.xml"  # still matches f"{uuid}*.xml"
    _touch_with_time(older, time.time() - 10)
    _touch_with_time(newer, time.time() + 10)

    chosen = mod.latest_flow_file(flows, uuid)
    assert chosen == newer  # exercises the same return line via mtime fallback
