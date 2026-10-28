from decimal import Decimal

import pytest

from shipping import shipping_cost


def test_exact_threshold_is_free():
    assert shipping_cost(Decimal("50.00")) == Decimal("0.00")


def test_below_threshold_has_fee():
    assert shipping_cost(Decimal("49.99")) == Decimal("4.99")


def test_above_threshold_is_free():
    assert shipping_cost(Decimal("50.01")) == Decimal("0.00")


def test_negative_subtotal_is_rejected():
    with pytest.raises(ValueError):
        shipping_cost(Decimal("-1.00"))
