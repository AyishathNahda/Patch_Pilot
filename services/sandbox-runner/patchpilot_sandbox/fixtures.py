"""Reviewed fixture registry. Manifests and request inputs cannot authorize execution."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

FixtureId = Literal["checkout-empty-cart", "shipping-threshold", "quantity-bool", "csv-quoted-fields"]
DEFAULT_FIXTURE: FixtureId = "checkout-empty-cart"
TEST_COMMAND = ("python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests")


@dataclass(frozen=True)
class Fixture:
    fixture_id: FixtureId
    name: str
    category: str
    description: str
    example_bug_description: str
    source_path: str
    test_path: str
    failing_test: str
    failure_marker: str
    expected_passed: int = 3
    expected_failed: int = 1

    @property
    def files(self) -> tuple[str, ...]:
        return (self.source_path, self.test_path, "manifest.json")


FIXTURES = MappingProxyType({fixture.fixture_id: fixture for fixture in (
    Fixture(DEFAULT_FIXTURE, "Checkout · empty cart", "edge_case",
            "An empty shopping cart should total Decimal zero while preserving discounts and validation.",
            "An empty shopping cart should return Decimal zero instead of raising IndexError. Preserve discounts and existing validation.",
            "checkout/__init__.py", "tests/test_checkout.py",
            "tests/test_checkout.py::test_empty_cart_returns_zero", "IndexError"),
    Fixture("shipping-threshold", "Shipping · free-delivery threshold", "business_logic",
            "Shipping costs 4.99 below a subtotal of 50.00 and is free at or above 50.00; negative subtotals are invalid.",
            "A subtotal of exactly 50.00 should qualify for free shipping. Preserve the fee below the threshold and negative-subtotal validation.",
            "shipping/__init__.py", "tests/test_shipping.py",
            "tests/test_shipping.py::test_exact_threshold_is_free", "AssertionError"),
    Fixture("quantity-bool", "Inventory · boolean quantity", "input_validation",
            "Quantities must be positive integers. Booleans, zero, negative numbers and non-integers must raise ValueError.",
            "validate_quantity(True) should raise ValueError rather than accepting a boolean as an integer. Preserve valid positive integers and other rejection cases.",
            "inventory/__init__.py", "tests/test_inventory.py",
            "tests/test_inventory.py::test_boolean_is_rejected", "DID NOT RAISE", expected_passed=5),
    Fixture("csv-quoted-fields", "CSV · quoted fields", "data_parsing",
            "Parse one CSV record with comma delimiters and double-quote escaping, preserving empty and trailing fields.",
            "Quoted commas in a CSV field should stay in one field. Preserve plain records, empty fields and trailing empty fields.",
            "record_parser/__init__.py", "tests/test_parser.py",
            "tests/test_parser.py::test_quoted_comma_stays_in_field", "AssertionError"),
)})


def get_fixture(fixture_id: str) -> Fixture:
    try:
        return FIXTURES[fixture_id]
    except KeyError:
        raise ValueError("Unknown fixture") from None
