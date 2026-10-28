from decimal import Decimal

import pytest

from checkout import calculate_total


def test_empty_cart_returns_zero():
    assert calculate_total([]) == Decimal("0.00")


def test_multiple_items():
    assert calculate_total([Decimal("10.00"), Decimal("5.50")]) == Decimal("15.50")


def test_percentage_discount():
    assert calculate_total([Decimal("20.00")], Decimal("0.25")) == Decimal("15.00")


def test_invalid_discount():
    with pytest.raises(ValueError, match="Discount"):
        calculate_total([Decimal("20.00")], Decimal("1.1"))
