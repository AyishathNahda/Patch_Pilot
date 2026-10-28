# Quoted CSV fields — parsing

Intended behavior: transform one CSV record into fields, respecting comma
delimiters and double-quote escaping, including commas inside quoted fields.
Preserve empty middle and trailing fields. The naive split is the deliberate
bug: a quoted comma produces an extra field. That test fails; plain/empty-field
regression tests pass. The Python standard library is sufficient for a fix.
Only run via the approved Docker runner. Keep the original source buggy.
