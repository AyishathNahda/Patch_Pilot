# Shipping threshold — business logic

Intended behavior: shipping is Decimal 4.99 below a Decimal subtotal of 50.00,
and Decimal zero at or above 50.00. Negative subtotals raise ValueError.
The deliberate strict-greater-than comparison excludes orders exactly at the
threshold. One deterministic test fails there; three cover below, above and
invalid negative totals. Application dependencies: Python standard library only.
Run only through the approved Docker runner, never host test discovery. Keep this
original benchmark buggy; candidate fixes belong in disposable copies.
