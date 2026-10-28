import pytest

from inventory import validate_quantity


def test_boolean_is_rejected():
    with pytest.raises(ValueError):
        validate_quantity(True)


def test_positive_integer_is_preserved():
    assert validate_quantity(3) == 3


def test_zero_is_rejected():
    with pytest.raises(ValueError):
        validate_quantity(0)


def test_fraction_is_rejected():
    with pytest.raises(ValueError):
        validate_quantity(1.5)


def test_negative_is_rejected():
    with pytest.raises(ValueError):
        validate_quantity(-2)


def test_false_is_rejected():
    with pytest.raises(ValueError):
        validate_quantity(False)
