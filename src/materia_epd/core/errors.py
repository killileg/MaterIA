class NoMatchingEPDError(Exception):
    """Raised when no EPDs match the given filters after all fallbacks."""

    def __init__(self, message="No matching EPDs found for the following filters:"):
        super().__init__(message)
