"""Normalize absent clause numbers without losing alphanumeric clauses."""


def normalize_clause_number(value: str | int | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("clause_number must be a string, integer or None")
    text = str(value).strip()
    return None if text in ("", "0") else text
