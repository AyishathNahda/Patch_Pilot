# Checkout empty-cart benchmark

`calculate_total` adds Decimal item prices and applies a fractional discount between
zero and one, rounding to cents. Negative prices and invalid discounts are rejected.
An empty cart should return `Decimal("0.00")`.

The implementation deliberately indexes the first price. The empty-cart test should
fail with `IndexError`; the other three tests should pass. Do not fix this benchmark
until a patch-generation milestone explicitly asks for it.

`manifest.json` describes expected evidence and the allowed command. The runner
keeps its own explicit allowlist: editing this manifest cannot authorize commands.
Run this fixture only via the Docker integration workflow in the root README.
