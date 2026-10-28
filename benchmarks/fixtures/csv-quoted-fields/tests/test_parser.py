from record_parser import parse_record


def test_quoted_comma_stays_in_field():
    assert parse_record('"Doe, Jane",42') == ["Doe, Jane", "42"]
    assert parse_record('"Say ""hi""",42') == ['Say "hi"', "42"]


def test_plain_record():
    assert parse_record("Ada,42") == ["Ada", "42"]


def test_empty_middle_field():
    assert parse_record("a,,b") == ["a", "", "b"]


def test_trailing_empty_field():
    assert parse_record("a,b,") == ["a", "b", ""]
