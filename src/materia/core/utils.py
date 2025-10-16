def to_float(value, positive=False):
    """Convert to float; if positive=True, return None for <= 0."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if (not positive or f > 0) else None
