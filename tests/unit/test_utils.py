# tests/unit/test_utils.py
import pytest
from materia.core import utils


@pytest.mark.parametrize(
    "value,expected",
    [
        (5, 5.0),
        ("3.14", 3.14),
        (0, 0.0),
        (-2.5, -2.5),
    ],
)
def test_to_float_basic(value, expected):
    """Ensure normal conversion to float works."""
    assert utils.to_float(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", ["abc", None, object(), ""])
def test_to_float_invalid_returns_none(value):
    """Invalid or non-numeric values should return None."""
    assert utils.to_float(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (10, 10.0),
        (0, None),
        (-3, None),
        ("4.2", 4.2),
        ("-1.0", None),
    ],
)
def test_to_float_positive_mode(value, expected):
    """When positive=True, should return None for non-positive numbers."""
    assert utils.to_float(value, positive=True) == expected


def test_to_float_type_error_and_value_error_handling():
    """Covers the except branch explicitly."""

    class Bad:
        def __float__(self):
            raise ValueError("cannot convert")

    assert utils.to_float(Bad()) is None


def test_extract_version_returns_tuple():
    """Ensure that version numbers are correctly extracted and split into ints."""
    # Simple pattern
    assert utils._extract_version("file_version1.0.2.xml") == (1, 0, 2)

    # With optional dot after 'version'
    assert utils._extract_version("data_version.10.4.txt") == (10, 4)

    # Case-insensitive and with prefix/suffix
    assert utils._extract_version("REPORT_Version2.5.0-extra") == (2, 5, 0)


def test_extract_version_returns_none_when_no_match():
    """Ensure that filenames without version pattern return None."""
    assert utils._extract_version("file_nover.txt") is None
    assert utils._extract_version("my_versionlessfile1_2_3.txt") is None
