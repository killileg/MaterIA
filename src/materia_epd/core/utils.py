import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def to_float(value, positive=False):
    """Convert to float; if positive=True, return None for <= 0."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if (not positive or f > 0) else None


def _extract_version(name: str) -> Optional[Tuple[int, ...]]:
    """Extract version tuple from filename (e.g. 1.0.2) or None if absent."""
    pattern = re.compile(r"version\.?(\d+(?:\.\d+)*)", re.IGNORECASE)
    match = pattern.search(name)
    if not match:
        return None
    return tuple(int(p) for p in match.group(1).split("."))


def sort_key(p: Path):
    v = _extract_version(p.name)
    return (
        v is not None,
        v or tuple(),
        p.stat().st_mtime,
    )


def print_progress(uuid: str, status: str, icon: str, overwrite=True):
    if overwrite:
        sys.stdout.write(f"\r{icon} {uuid}: {status}")
        sys.stdout.flush()
    else:
        sys.stdout.write("\r" + " " * 80 + "\r")
        print(f"{icon} {uuid}: {status}")


def qn_uri(uri: str, name: str) -> str:
    return f"{{{uri}}}{name}"
