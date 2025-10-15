class NoMatchingEPDError(Exception):
    """Raised when no EPDs match the given filters after all fallbacks."""

    def __init__(self, message="No matching EPDs found for the following filters:"):
        super().__init__(message)


class LocationNotFoundError(Exception):
    """Raised when a location code is not found in the location files."""

    def __init__(self, message="No matching location file:"):
        super().__init__(message)
