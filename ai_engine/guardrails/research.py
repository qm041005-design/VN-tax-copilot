"""SCRUM-23: guarded orchestration, independent of a specific LLM vendor.

All passages/assessments come from trusted server components after access checks.
Never bind assessments or allowed IDs directly from a public request body.
"""
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .abstention import EvidenceAssessment, decide_abstention
from .pipeline import prepare_research
from .redaction import redact_text
from .contract import validate_output


@dataclass(frozen=True)
class ResearchContext:
    tax_period: str | None = None
    material_facts: str | None = None
    # Set server-side according to the use case. General definitions can opt out.
    require_tax_period: bool = True
    require_material_facts: bool = True


@dataclass(frozen=True)
class Claim:
    text: str
    citation_ids: tuple[str | int, ...]
    section: str = "analysis"


@dataclass(frozen=True)
class GeneratedResearch:
    # Every legal assertion must be represented as a separately cited claim.
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class ResearchResult:
    status: str  # clarify | abstain | draft
    reason: str
    message: str = ""
    answer: str | None = None
    citation_ids: tuple[str | int, ...] = ()
    questions: tuple[str, ...] = ()
    payload: dict | None = None


@dataclass(frozen=True)
class SafeResearchInput:
    query: str
    tax_period: str
    material_facts: str
    passages: tuple[dict, ...]


Assessor = Callable[[SafeResearchInput], Sequence[EvidenceAssessment]]
Generator = Callable[[SafeResearchInput], GeneratedResearch | dict | str]


def validate_citations(generated: GeneratedResearch, allowed_ids: Sequence[str | int]) -> bool:
    """Validate structured claims against the exact sources passed to generation.

    Strict ID types avoid treating True/1 or numeric strings/integers as the same
    source. Membership is not semantic entailment or temporal validity.
    """
    if not isinstance(generated, GeneratedResearch) or not generated.claims:
        return False
    if any(type(pid) not in (str, int) for pid in allowed_ids):
        return False
    allowed = {(type(pid), pid) for pid in allowed_ids}
    for claim in generated.claims:
        if not isinstance(claim, Claim) or not isinstance(claim.text, str) or not claim.text.strip():
            return False
        if not isinstance(claim.citation_ids, (tuple, list)) or not claim.citation_ids:
            return False
        for pid in claim.citation_ids:
            if type(pid) not in (str, int) or (type(pid), pid) not in allowed:
                return False
    return True


def run_guarded_research(
    query: str,
    passages: Sequence[Mapping],
    context: ResearchContext,
    *,
    assess: Assessor | None = None,
    generate: Generator | None = None,
) -> ResearchResult:
    """No generation on missing facts, absent assessor or insufficient evidence.

    Context adequacy (not just nonblank fields), effective dates, conflicts and
    relevance remain the trusted assessor's responsibility. No raw inputs or
    provider exception text are returned/logged here.
    """
    if not isinstance(query, str) or not query.strip():
        return ResearchResult("clarify", "empty_query", questions=("Bạn cần tra cứu vấn đề thuế nào?",))
    missing = []
    if context.require_tax_period and not (context.tax_period or "").strip():
        missing.append("Bạn cần áp dụng cho kỳ thuế hoặc năm nào?")
    if context.require_material_facts and not (context.material_facts or "").strip():
        missing.append("Vui lòng bổ sung tình huống, giao dịch và đối tượng áp dụng.")
    if missing:
        return ResearchResult("clarify", "missing_context", questions=tuple(missing))
    try:
        prepared = prepare_research(query, passages)
        safe = SafeResearchInput(
            prepared.query,
            redact_text(context.tax_period or "").text,
            redact_text(context.material_facts or "").text,
            prepared.passages,
        )
        # Validate structural source integrity before calling any AI component.
        gate = decide_abstention(safe.query, safe.passages)
        if gate.reason != "insufficient_evidence":
            return ResearchResult("abstain", gate.reason, gate.message)
        if assess is None:
            return ResearchResult("abstain", "assessment_unavailable", "Chưa có bộ đánh giá căn cứ; cần chuyên gia thẩm định.")
        # Give assessor a separate copy so mutations cannot change the generation whitelist.
        assessed_input = SafeResearchInput(safe.query, safe.tax_period, safe.material_facts,
                                          tuple(dict(p) for p in safe.passages))
        assessments = tuple(assess(assessed_input))
        if any(not isinstance(a, EvidenceAssessment) for a in assessments):
            raise ValueError("invalid assessment shape")
        # Avoid bool/int ID aliasing in the legacy gate.
        valid_ids = {(type(p["passage_id"]), p["passage_id"]) for p in safe.passages}
        if any((type(a.passage_id), a.passage_id) not in valid_ids for a in assessments):
            raise ValueError("assessment ID mismatch")
        gate = decide_abstention(safe.query, safe.passages, assessments)
        if gate.should_abstain:
            return ResearchResult("abstain", gate.reason, gate.message)
        if generate is None:
            return ResearchResult("abstain", "generation_unavailable", "Chưa cấu hình bộ sinh câu trả lời.")
        selected = tuple(dict(p) for p in safe.passages if p["passage_id"] in gate.evidence_ids)
        # Snapshot before handing mutable passage dictionaries to a callback.
        allowed = tuple(p["passage_id"] for p in selected)
        generated = generate(SafeResearchInput(safe.query, safe.tax_period, safe.material_facts, selected))
        if isinstance(generated, (dict, str)):
            try:
                payload = validate_output(generated, allowed)
            except (ValueError, TypeError):
                return ResearchResult("abstain", "invalid_citations_or_output", "Đầu ra AI không đạt kiểm tra cấu trúc hoặc trích dẫn; đã chặn kết quả.")
            if payload["status"] != "draft":
                return ResearchResult(payload["status"], "provider_requested_" + payload["status"],
                                      questions=tuple(payload["clarification_questions"]), payload=payload)
            ids = tuple(dict.fromkeys(pid for entries in payload["sections"].values()
                                      for entry in entries for pid in entry["citation_ids"]))
            answer = "\n".join(entry["text"] for entries in payload["sections"].values() for entry in entries)
            payload["warnings"].append("Bản dự thảo AI; cần chuyên gia kiểm tra nội dung và căn cứ.")
            return ResearchResult("draft", "validated_source_ids", answer=answer, citation_ids=ids, payload=payload)
        if not validate_citations(generated, allowed):
            return ResearchResult("abstain", "invalid_citations", "Câu trả lời có trích dẫn thiếu hoặc ngoài tập nguồn được phép; đã chặn kết quả.")
        # Legacy Claim adapter: callers must label authority and analysis explicitly.
        from .contract import SECTION_NAMES
        payload = {"status": "draft", "sections": {name: [] for name in SECTION_NAMES},
                   "clarification_questions": [], "warnings": []}
        for claim in generated.claims:
            if claim.section not in payload["sections"]:
                raise ValueError("unknown section")
            payload["sections"][claim.section].append({"text": claim.text, "citation_ids": list(claim.citation_ids)})
        try:
            payload = validate_output(payload, allowed)
        except (ValueError, TypeError):
            return ResearchResult("abstain", "invalid_citations_or_output", "Thiếu căn cứ hoặc cấu trúc sáu phần hợp lệ.")
        ids = tuple(dict.fromkeys(pid for c in generated.claims for pid in c.citation_ids))
        answer = "\n".join(redact_text(c.text).text for c in generated.claims)
        payload["warnings"].append("Bản dự thảo AI; cần chuyên gia kiểm tra nội dung và căn cứ.")
        return ResearchResult("draft", "validated_source_ids", answer=answer, citation_ids=ids, payload=payload)
    except Exception:
        # Provider exceptions may embed prompts/PII; do not propagate their messages.
        return ResearchResult("abstain", "guardrail_or_provider_error", "Không thể hoàn tất kiểm tra an toàn; chưa phát hành câu trả lời.")
