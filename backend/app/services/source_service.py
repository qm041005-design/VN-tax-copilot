"""
app/services/source_service.py  –  TÌM KIẾM & XEM NGUỒN LUẬT (đọc bảng legal_documents / legal_chunks)
=====================================================================================================
Văn bản pháp luật là dữ liệu CÔNG KHAI, dùng chung mọi tenant -> không lọc theo tenant_id
(nhưng endpoint vẫn bắt đăng nhập).
"""
import re
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from app.schemas.source import SourceDetail, SourceHit
from app.services.legal_metadata import clause_label, period_bounds
from ai_engine.retrieval.bm25 import BM25Retriever

MAX_TERMS = 20
SNIPPET_LEN = 300


def _terms(q: str) -> list[str]:
    """Tách câu hỏi thành từ (bỏ dấu câu, trùng lặp), tối đa MAX_TERMS từ."""
    return list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", q)))[:MAX_TERMS]


def search(db: Session, q: str, doc_type: str | None = None, as_of: date | None = None,
           limit: int = 10, *, tax_type: str | None = None,
           tax_period: str | None = None) -> list[tuple[LegalChunk, float]]:
    """Filter candidates before BM25; date overlap is NOT legal applicability.

    A tax period takes precedence over the research date. Unknown legal dates
    remain candidates for expert checking, never verified authorities.
    """
    if not _terms(q):
        return []
    stmt = select(LegalChunk).join(LegalChunk.document).options(contains_eager(LegalChunk.document))
    if doc_type:
        stmt = stmt.where(LegalDocument.doc_type == doc_type.upper())
    if tax_type:
        stmt = stmt.where(LegalDocument.id.in_(select(LegalDocumentTaxScope.doc_id).where(
            LegalDocumentTaxScope.tax_type == tax_type)))
    bounds = period_bounds(tax_period)
    if bounds or as_of:
        start, end = bounds or (as_of, as_of)
        stmt = stmt.where(
            (LegalDocument.effective_date.is_(None)) |
            (LegalDocument.effective_date <= datetime.combine(end, time.max)),
            (LegalDocument.expiry_date.is_(None)) |
            (LegalDocument.expiry_date > datetime.combine(start, time.min)))
    chunks = list(db.scalars(stmt.order_by(LegalChunk.id)).all())
    lookup = {str(c.id): c for c in chunks}
    hits = BM25Retriever([{"passage_id": str(c.id), "text": c.content,
                           "legal_identifier": c.document.doc_code} for c in chunks]).search(q, limit)
    return [(lookup[h["passage_id"]], h["score"]) for h in hits]


def get_chunk(db: Session, chunk_id: int) -> LegalChunk | None:
    return db.scalar(select(LegalChunk).join(LegalChunk.document)
                     .options(contains_eager(LegalChunk.document)).where(LegalChunk.id == chunk_id))


def to_hit(chunk: LegalChunk) -> SourceHit:
    doc = chunk.document
    return SourceHit(
        source_id=str(chunk.id), title=doc.title, legal_identifier=doc.doc_code,
        dieu=chunk.article_number, khoan=clause_label(chunk.clause_number),
        diem=chunk.point_letter or None, url=doc.source_url, citation_path=chunk.citation_path,
        doc_type=doc.doc_type, hierarchy_level=chunk.hierarchy_level,
        effective_date=doc.effective_date, expiry_date=doc.expiry_date,
        snippet=chunk.content[:SNIPPET_LEN],
    )


def to_detail(chunk: LegalChunk) -> SourceDetail:
    doc = chunk.document
    return SourceDetail(**to_hit(chunk).model_dump(), content=chunk.content, article_title=chunk.article_title,
                        issuer=doc.issuer, version=doc.version, source_page=chunk.source_page)
