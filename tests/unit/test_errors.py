# tests/unit/test_errors.py
import pytest

from materia_epd.core.errors import NoMatchingEPDError


def test_no_matching_epd_error_default_message():
    with pytest.raises(NoMatchingEPDError) as exc:
        raise NoMatchingEPDError()
    assert isinstance(exc.value, Exception)
    assert str(exc.value) == "No matching EPDs found for the following filters:"


def test_no_matching_epd_error_custom_message():
    with pytest.raises(NoMatchingEPDError) as exc:
        raise NoMatchingEPDError("Nothing matched")
    assert str(exc.value) == "Nothing matched"
