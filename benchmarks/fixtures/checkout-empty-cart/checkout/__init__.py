"""Small checkout calculation benchmark."""

from decimal import Decimal


def calculate_total(prices: list[Decimal], discount: Decimal = Decimal("0")) -> Decimal:
    """Return the discounted total, rounded to cents; discount is a fraction."""
    if not Decimal("0") <= discount <= Decimal("1"):
        raise ValueError("Discount must be between zero and one")
    if any(price < 0 for price in prices):
        raise ValueError("Prices cannot be negative")
    # Deliberate benchmark bug: the first-item assumption breaks empty carts.
    subtotal = prices[0] + sum(prices[1:], Decimal("0"))
    return (subtotal * (1 - discount)).quantize(Decimal("0.01"))
