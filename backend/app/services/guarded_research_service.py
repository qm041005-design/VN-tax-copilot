"""SCRUM-23 adapter: SQL search rows -> guarded AI pipeline.

Run backend with repository root on PYTHONPATH so ai_engine is importable.
Callbacks are injected by server code, never request-body fields.
"""
from ai_engine.guardrails import ResearchContext, run_guarded_research


def research_from_rows(question, rows, *, tax_period=None, material_facts=None,
                       assess=None, generate=None):
    passages = [
        {"passage_id": str(chunk.id), "legal_identifier": chunk.document.doc_code,
         "text": chunk.content,
         "dieu": getattr(chunk, "article_number", None),
         "khoan": str(chunk.clause_number) if getattr(chunk, "clause_number", 0) else None,
         "diem": getattr(chunk, "point_letter", None) or None,
         "doc_type": getattr(chunk.document, "doc_type", None),
         "effective_date": chunk.document.effective_date.isoformat() if getattr(chunk.document, "effective_date", None) else None,
         "expiry_date": chunk.document.expiry_date.isoformat() if getattr(chunk.document, "expiry_date", None) else None,
         "version": getattr(chunk.document, "version", None),
         "source_page": getattr(chunk, "source_page", None)}
        for chunk, _score in rows
    ]
    return run_guarded_research(
        question, passages, ResearchContext(tax_period, material_facts),
        assess=assess, generate=generate,
    )
