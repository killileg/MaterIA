from pathlib import Path
import json
import xml.etree.ElementTree as ET


def read_json_file(path):
    """Return JSON content or None if invalid."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json_file(path, data) -> bool:
    """Write JSON content to a file. Returns True if successful, False otherwise."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except (OSError, TypeError, ValueError):
        return False


def read_xml_root(path: Path | str):
    try:
        return ET.parse(path).getroot()
    except (FileNotFoundError, ET.ParseError) as e:
        print(f"Error reading XML root from {path}: {e}")
        return None


def write_xml_root(root: ET.Element, path: Path | str) -> bool:
    """Write XML root to file. Returns True if successful."""
    try:
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        return True
    except Exception:
        return False


def gen_json_objects(folder_path):
    """Yield (file, data) for valid JSON files in folder."""
    for file in Path(folder_path).glob("*.json"):
        data = read_json_file(file)
        if data is not None:
            yield file, data


def gen_xml_objects(folder_path):
    """Yield (file, root) for valid XML files in folder."""
    for file in Path(folder_path).glob("*.xml"):
        root = read_xml_root(file)
        if root is not None:
            yield file, root
