# tests/unit/test_errors.py
import pytest

from materia.core.errors import NoMatchingEPDError, LocationNotFoundError


def test_no_matching_epd_error_default_message():
    with pytest.raises(NoMatchingEPDError) as exc:
        raise NoMatchingEPDError()
    assert isinstance(exc.value, Exception)
    assert str(exc.value) == "No matching EPDs found for the following filters:"


def test_no_matching_epd_error_custom_message():
    with pytest.raises(NoMatchingEPDError) as exc:
        raise NoMatchingEPDError("Nothing matched")
    assert str(exc.value) == "Nothing matched"


def test_location_not_found_error_default_message():
    with pytest.raises(LocationNotFoundError) as exc:
        raise LocationNotFoundError()
    assert isinstance(exc.value, Exception)
    assert str(exc.value) == "No matching location file:"


def test_location_not_found_error_custom_message():
    with pytest.raises(LocationNotFoundError) as exc:
        raise LocationNotFoundError("Missing FR.json")
    assert str(exc.value) == "Missing FR.json"
