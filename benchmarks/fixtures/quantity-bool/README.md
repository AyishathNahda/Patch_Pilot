# Boolean quantity — input validation

Intended behavior: accept positive integers and return them unchanged. Reject
booleans, zero, negative values and non-integers with ValueError. Python booleans
subclass int: the deliberate isinstance-only check wrongly accepts True.
The True rejection test fails; five positive, zero, fractional, negative and False tests regress
existing behavior. No application dependencies beyond Python itself.
Run only through the approved Docker runner. Never fix the original fixture;
apply candidates to disposable copies.
