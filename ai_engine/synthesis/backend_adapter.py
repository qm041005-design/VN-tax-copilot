"""SCRUM-17: trusted backend metadata -> prompt and export contracts.

Call only after matter/source authorization and server-side guardrails. This
module neither assesses legal support nor grants approval or calls a provider.
"""
from copy import deepcopy

from .prompt_templates import SECTION_LABELS, build_messages


def _label(value):
    if value is None:
        return None
    if type(value) not in (str, int):
        raise ValueError("Citation labels must be text or integers")
    label = str(value).strip()
    return None if label in ("", "0") else label


def source_details_to_passages(details, *, allowed_source_ids):
    """Map authorized SourceDetail objects; never substitute a search snippet."""
    if not isinstance(details, list):
        raise ValueError("SourceDetail list required")
    allowed = set(allowed_source_ids)
    if any(not isinstance(pid, str) or not pid.strip() for pid in allowed):
        raise ValueError("Authorized source IDs must be nonempty strings")
    passages, seen = [], set()
    for detail in details:
        if not isinstance(detail, dict):
            raise ValueError("SourceDetail must be an object")
        pid = detail.get("source_id")
        if not isinstance(pid, str) or pid not in allowed or pid in seen:
            raise ValueError("Duplicate or unauthorized source_id")
        text = detail.get("content")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Full SourceDetail.content required; snippet is insufficient")
        seen.add(pid)
        passage = {"passage_id": pid, "text": text,
                   "dieu": _label(detail.get("dieu")),
                   "khoan": _label(detail.get("khoan")),
                   "diem": _label(detail.get("diem"))}
        for key in ("legal_identifier", "title", "url", "doc_type", "hierarchy_level",
                    "effective_date", "expiry_date", "version", "source_page", "status"):
            passage[key] = detail.get(key)
        passages.append(passage)
    return passages


def build_backend_messages(request, details, *, allowed_source_ids):
    """Request context must already include explicit, resolved matter defaults.

    Apply the deployment's redaction policy before sending these messages to an
    external provider. Source URLs are provenance, never instructions to fetch.
    """
    passages = source_details_to_passages(details, allowed_source_ids=allowed_source_ids)
    return build_messages(request.get("question"), passages,
                          facts=request.get("material_facts") or "",
                          tax_period=request.get("tax_period"),
                          research_as_of=request.get("research_as_of"))


def build_guarded_messages(safe_input):
    """Generator callback adapter for An's already-redacted SafeResearchInput.

    The guardrails pipeline selects the evidence before calling the generator.
    Do not construct safe_input from a public request to bypass that gate.
    """
    return build_messages(safe_input.query, list(safe_input.passages),
                          facts=safe_input.material_facts, tax_period=safe_input.tax_period)


def prepare_backend_export(response, details, *, matter_id):
    """Return (six-section result, trusted export sources) from a server response.

    History citations are candidates on clarify/abstain, never inferred claims.
    Missing persisted research_result is an error, not a reconstructed answer.
    """
    history = response.get("history", {})
    if not matter_id or history.get("matter_id") != matter_id:
        raise ValueError("Research response belongs to a different matter")
    result = response.get("research_result")
    required = {"status", "sections", "clarification_questions", "warnings"}
    if not isinstance(result, dict) or set(result) != required:
        raise ValueError("Guarded research_result required; history.answer is insufficient")
    if result["status"] not in ("draft", "clarify", "abstain"):
        raise ValueError("Unsupported research status; AI cannot approve")
    if not isinstance(result["sections"], dict) or set(result["sections"]) != set(SECTION_LABELS):
        raise ValueError("Exactly six sections required")
    for field in ("warnings", "clarification_questions"):
        if not isinstance(result[field], list) or any(not isinstance(v, str) or not v.strip() for v in result[field]):
            raise ValueError("Invalid research messages")
    clean = deepcopy(result)
    if clean["status"] != "draft":
        # Match guardrails: a refusal cannot publish legal claims from a payload.
        clean["sections"] = {key: [] for key in SECTION_LABELS}
    elif clean["clarification_questions"]:
        raise ValueError("Draft has unresolved clarification questions")
    if clean["status"] == "clarify" and not clean["clarification_questions"]:
        raise ValueError("Clarify requires questions")
    hits = response.get("sources")
    if not isinstance(hits, list) or any(not isinstance(h, dict) for h in hits):
        raise ValueError("Backend source list required")
    hit_ids = [h.get("source_id") for h in hits]
    if any(not isinstance(pid, str) or not pid.strip() for pid in hit_ids) or len(set(hit_ids)) != len(hit_ids):
        raise ValueError("Invalid or duplicate backend source IDs")
    passages = source_details_to_passages(details, allowed_source_ids=hit_ids)
    hits_by_id = {h["source_id"]: h for h in hits}
    for passage in passages:
        hit = hits_by_id[passage["passage_id"]]
        for key in ("legal_identifier", "url", "dieu", "khoan", "diem"):
            value = _label(hit.get(key)) if key in ("dieu", "khoan", "diem") else hit.get(key)
            if passage[key] != value:
                raise ValueError("SourceDetail metadata differs from the research source snapshot")
    sources = {}
    for p in passages:
        sources[p["passage_id"]] = dict(
            document_number=p["legal_identifier"], article=("Điều " + p["dieu"]) if p["dieu"] else None,
            clause=("Khoản " + p["khoan"]) if p["khoan"] else None,
            point=("Điểm " + p["diem"]) if p["diem"] else None, source_url=p["url"],
            source_page=p["source_page"], version_note=("Phiên bản lưu trữ: " + p["version"])
            if isinstance(p["version"], str) and p["version"].strip() else None)
    cited = set()
    for name, entries in clean["sections"].items():
        if not isinstance(entries, list):
            raise ValueError("Section must be a list")
        for item in entries:
            if not isinstance(item, dict) or set(item) != {"text", "citation_ids"}:
                raise ValueError("Invalid section item")
            ids = item["citation_ids"]
            if not isinstance(ids, list) or any(not isinstance(pid, str) or pid not in sources for pid in ids):
                raise ValueError("Citation lacks authorized full-text SourceDetail")
            cited.update(ids)
    # Pin each claim to the guardrails-accepted history citation IDs as well.
    if clean["status"] == "draft":
        citations = history.get("citations")
        if not isinstance(citations, list) or any(not isinstance(c, dict) for c in citations):
            raise ValueError("Validated history citations required")
        if not cited <= {c.get("source_id") for c in citations}:
            raise ValueError("Citation was not accepted by backend guardrails")
        for pid in cited:
            if type(sources[pid]["source_page"]) is not int or sources[pid]["source_page"] < 1:
                raise ValueError("Cited source requires a verified PDF page number")
            if not sources[pid]["version_note"]:
                raise ValueError("Cited source requires a storage version")
    return clean, sources
