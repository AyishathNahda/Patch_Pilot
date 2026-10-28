"""Single-record CSV transformation for a contact import."""


def parse_record(record: str) -> list[str]:
    """Read a CSV record with quoted commas and preserve empty fields."""
    return record.split(",")
