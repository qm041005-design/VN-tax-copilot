"""Conservative, local redaction. Never retain original matched values."""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    counts: dict[str, int]


# Order matters: labelled identifiers take precedence over phone-like numbers.
_RULES = (
    ("MST", re.compile(r"(?P<label>\b(?:MST|mã\s+số\s+thuế)\s*[:：=]?\s*)(?P<value>(?<!\d)\d{10}(?:-?\d{3})?(?!\d))", re.I)),
    ("CCCD", re.compile(r"(?<!\w)\d{12}(?!\w)")),
    ("CMND", re.compile(r"(?P<label>\bCMND\s*[:：=]?\s*)(?P<value>\d{9}(?!\d))", re.I)),
    ("EMAIL", re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)),
    ("MST", re.compile(r"(?<![\w/])\d{10}-\d{3}(?![\w/])")),
    ("PHONE", re.compile(r"(?<![\w/+])(?:\+84|0084|0)[ .-]?[35789](?:[ .-]?\d){8}(?!\w)")),
    ("MST", re.compile(r"(?<![\w/])\d{10}(?![\w/])")),
)


def redact_text(text: str) -> RedactionResult:
    """Mask common identifiers; ten-digit numbers are masked conservatively.

    NFC/NFKC handles decomposed labels and full-width digits. This is not a
    general named-entity detector: names, addresses and payroll need upstream
    structured-field filtering. Call on every outbound text, including sources.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    clean = unicodedata.normalize("NFKC", text)
    counts: dict[str, int] = {}
    for kind, pattern in _RULES:
        def replace(match, kind=kind):
            counts[kind] = counts.get(kind, 0) + 1
            label = match.groupdict().get("label", "")
            return f"{label}[REDACTED_{kind}]"
        clean = pattern.sub(replace, clean)
    return RedactionResult(clean, counts)
