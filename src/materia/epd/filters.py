from __future__ import annotations
from materia.epd.models import IlcdProcess


class EPDFilter:
    def matches(self, epd: IlcdProcess) -> bool:
        return True

    def __repr__(self):
        return self.__class__.__name__


class UUIDFilter(EPDFilter):
    def __init__(self, matches: list):
        self.uuids = (
            matches.get("uuids", matches) if isinstance(matches, dict) else matches
        )

    def matches(self, epd: IlcdProcess) -> bool:
        return epd.uuid in self.uuids

    def __repr__(self):
        return f"{self.__class__.__name__}(uuids={self.uuids})"


class UnitConformityFilter(EPDFilter):
    def __init__(self, target_kwargs):
        self.target_kwargs = target_kwargs

    def matches(self, epd: IlcdProcess) -> bool:
        try:
            epd.get_ref_flow()
            epd.material.rescale(self.target_kwargs)
            return True
        except ValueError:
            return False

    def __repr__(self):
        return f"{self.__class__.__name__}(target={self.target_kwargs})"


class LocationFilter(EPDFilter):
    def __init__(self, locations):
        self.locations = locations

    def matches(self, epd: IlcdProcess) -> bool:
        return epd.loc in self.locations

    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.locations})"
