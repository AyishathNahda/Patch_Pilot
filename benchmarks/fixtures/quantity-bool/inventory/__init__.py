"""Quantity validation at an inventory service boundary."""


def validate_quantity(value: object) -> int:
    """Accept only positive integers; booleans are not valid quantities."""
    if not isinstance(value, int) or value <= 0:
        raise ValueError("Quantity must be a positive integer")
    return value
