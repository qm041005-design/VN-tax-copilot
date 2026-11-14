"""Prepare a redacted evidence bundle before any external assessment or LLM."""
from dataclasses import dataclass
from typing import Mapping, Sequence

from .redaction import redact_text


@dataclass(frozen=True)
class PreparedResearch:
    query: str
    passages: tuple[dict, ...]


def prepare_research(query: str, passages: Sequence[Mapping]) -> PreparedResearch:
    """Whitelist BM25 fields; discard arbitrary metadata that may contain PII.

    IDs must be opaque internal identifiers. Source URLs/client names should not
    be used as passage IDs. Source provenance stays server-side, keyed by ID.
    """
    safe = []
    for passage in passages:
        pid = passage.get("passage_id")
        if type(pid) not in (str, int):
            raise ValueError("passage_id must be an opaque string or integer")
        if isinstance(pid, str) and redact_text(pid).text != pid:
            raise ValueError("passage_id must not contain detected personal data")
        item = {"passage_id": pid}
        for key in ("text", "legal_identifier"):
            value = passage.get(key, "")
            if not isinstance(value, str):
                raise TypeError(f"{key} must be a string")
            item[key] = redact_text(value).text
        # Explicit scalar metadata whitelist for pinpoint prompts; no client metadata.
        for key in ("dieu", "khoan", "diem", "doc_type", "effective_date", "expiry_date", "version", "source_page"):
            value = passage.get(key)
            if value is None:
                item[key] = None
            elif isinstance(value, (str, int)) and not isinstance(value, bool):
                item[key] = redact_text(str(value)).text
            else:
                raise TypeError(f"{key} must be scalar text or integer")
        safe.append(item)
    return PreparedResearch(redact_text(query).text, tuple(safe))
