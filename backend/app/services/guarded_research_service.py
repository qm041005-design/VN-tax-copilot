"""SCRUM-23 adapter: SQL search rows -> guarded AI pipeline.

Run backend with repository root on PYTHONPATH so ai_engine is importable.
Callbacks are injected by server code, never request-body fields.
"""
from datetime import date

from ai_engine.guardrails import ResearchContext, run_guarded_research
from app.models.legal_source import STATUS_UNKNOWN
from .legal_metadata import clause_label, date_status, period_bounds


def _status(chunk, start, end):
    """Trạng thái ghi sẵn (chuyên gia/registry) ưu tiên; không có thì tính từ ngày trong kỳ tra cứu.
    Đổi trạng thái giữa kỳ -> CHUA_XAC_DINH để guardrails chặn, không đoán."""
    doc = chunk.document
    stored = next((s for s in (getattr(chunk, "status", None), getattr(doc, "status", None))
                   if s and s != STATUS_UNKNOWN), None)
    if stored:
        return stored
    eff = getattr(chunk, "effective_date", None) or getattr(doc, "effective_date", None)
    exp = getattr(chunk, "expiry_date", None) or getattr(doc, "expiry_date", None)
    first, last = date_status(eff, exp, start), date_status(eff, exp, end)
    return first if first == last else STATUS_UNKNOWN


def research_from_rows(question, rows, *, tax_period=None, material_facts=None,
                       assess=None, generate=None, scenario=None, case_facts=None, as_of=None):
    start, end = period_bounds(tax_period) or (as_of or date.today(),) * 2
    passages = [
        {"passage_id": str(chunk.id), "legal_identifier": chunk.document.doc_code,
         "text": chunk.content,
         "dieu": getattr(chunk, "article_number", None),
         "khoan": clause_label(getattr(chunk, "clause_number", None)),
         "diem": getattr(chunk, "point_letter", None) or None,
         "doc_type": getattr(chunk.document, "doc_type", None),
         "effective_date": chunk.effective_date.isoformat() if getattr(chunk, "effective_date", None) else None,
         "expiry_date": (e.isoformat() if (e := getattr(chunk, "expiry_date", None) or getattr(chunk.document, "expiry_date", None)) else None),
         "version": getattr(chunk, "version", None),
         "status": _status(chunk, start, end),
         "document_effective_date": chunk.document.effective_date.isoformat() if getattr(chunk.document, "effective_date", None) else None,
         "document_version": getattr(chunk.document, "version", None),
         "source_page": getattr(chunk, "source_page", None)}
        for chunk, _score in rows
    ]
    return run_guarded_research(
        question, passages, ResearchContext(tax_period, material_facts, scenario=scenario, case_facts=case_facts),
        assess=assess, generate=generate,
    )
