"""Shipping charges for a small order service."""

from decimal import Decimal


def shipping_cost(subtotal: Decimal) -> Decimal:
    """Charge 4.99 below 50.00; orders at or above 50.00 ship free."""
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative")
    if subtotal > Decimal("50.00"):
        return Decimal("0.00")
    return Decimal("4.99")
