"""Strict boundary for the proposed week-3 six-section prompt contract."""
import json

from .redaction import redact_text

SECTION_NAMES = ("issue", "facts", "authority", "analysis", "limitations", "next_steps")


def validate_output(payload, allowed_ids):
    """Return a redacted copy, or raise ValueError. Never trust provider metadata.

    authority/analysis require citations on every item; other sections may carry
    uncited facts or process instructions, but any supplied ID must be allowed.
    This validates structure and ID membership, not legal entailment.
    """
    if isinstance(payload, str):
        if len(payload) > 100_000:
            raise ValueError("response too large")
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        payload = json.loads(payload, object_pairs_hook=unique_pairs)
    if not isinstance(payload, dict) or set(payload) != {"status", "sections", "clarification_questions", "warnings"}:
        raise ValueError("invalid response keys")
    status = payload["status"]
    if status not in ("draft", "clarify", "abstain"):
        raise ValueError("invalid status")
    sections = payload["sections"]
    if not isinstance(sections, dict) or set(sections) != set(SECTION_NAMES):
        raise ValueError("six sections required")
    if any(not isinstance(pid, str) or not pid.strip() for pid in allowed_ids):
        raise ValueError("contract requires string source IDs")
    allowed = set(allowed_ids)
    clean = {"status": status, "sections": {}, "clarification_questions": [], "warnings": []}
    for name in SECTION_NAMES:
        entries = sections[name]
        if not isinstance(entries, list):
            raise ValueError("section must be a list")
        clean["sections"][name] = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"text", "citation_ids"}:
                raise ValueError("invalid section item")
            text, ids = entry["text"], entry["citation_ids"]
            if not isinstance(text, str) or not text.strip() or not isinstance(ids, list):
                raise ValueError("invalid text or citations")
            if any(not isinstance(pid, str) or pid not in allowed for pid in ids):
                raise ValueError("citation outside allowed sources")
            if name in ("authority", "analysis") and not ids:
                raise ValueError("legal claim requires citation")
            clean["sections"][name].append({"text": redact_text(text).text, "citation_ids": list(dict.fromkeys(ids))})
    for key in ("clarification_questions", "warnings"):
        values = payload[key]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError("invalid messages")
        clean[key] = [redact_text(v).text for v in values]
    if status == "draft" and (not sections["authority"] or not sections["analysis"]):
        raise ValueError("draft needs authority and analysis")
    if status == "draft" and clean["clarification_questions"]:
        raise ValueError("unresolved clarification in draft")
    if status == "clarify" and not clean["clarification_questions"]:
        raise ValueError("clarify needs questions")
    # Never publish possible legal conclusions returned with a non-draft status.
    if status != "draft":
        clean["sections"] = {name: [] for name in SECTION_NAMES}
    return clean


def to_contract(result):
    """Serialize ResearchResult for prompt/export adapters, not an API migration."""
    if result.payload is not None:
        return validate_output(result.payload, result.citation_ids)
    return {
        "status": result.status,
        "sections": {name: [] for name in SECTION_NAMES},
        "clarification_questions": list(result.questions),
        "warnings": [v for v in (result.reason, result.message) if v],
    }
