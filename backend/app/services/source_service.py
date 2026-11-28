"""
app/services/source_service.py  –  TÌM KIẾM & XEM NGUỒN LUẬT (đọc bảng legal_documents / legal_chunks)
=====================================================================================================
Văn bản pháp luật là dữ liệu CÔNG KHAI, dùng chung mọi tenant -> không lọc theo tenant_id
(nhưng endpoint vẫn bắt đăng nhập).
"""
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from app.models.legal_source import STATUS_UNKNOWN
from app.schemas.source import SourceDetail, SourceHit
from app.services.legal_metadata import clause_label, date_status, period_bounds
from ai_engine.retrieval.bm25 import BM25Retriever, tokenize

SNIPPET_LEN = 300


def search(db: Session, q: str, doc_type: str | None = None, as_of: date | None = None,
           limit: int = 10, *, tax_type: str | None = None,
           tax_period: str | None = None) -> list[tuple[LegalChunk, float]]:
    """Filter candidates before BM25; date overlap is NOT legal applicability.

    A tax period takes precedence over the research date. Unknown legal dates
    remain candidates for expert checking, never verified authorities.
    """
    if limit <= 0 or not tokenize(q):
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
            (LegalDocument.expiry_date > datetime.combine(start, time.min)),
            # Một Khoản/Điểm sửa đổi có thể có ngày hiệu lực riêng, muộn hơn văn bản chứa nó
            (LegalChunk.effective_date.is_(None)) |
            (LegalChunk.effective_date <= datetime.combine(end, time.max)),
            (LegalChunk.expiry_date.is_(None)) |
            (LegalChunk.expiry_date > datetime.combine(start, time.min)))
    chunks = list(db.scalars(stmt.order_by(LegalChunk.id)).all())
    lookup = {str(c.id): c for c in chunks}
    passages = [
        {"passage_id": str(c.id), "text": c.content, "article_title": c.article_title,
         "legal_identifier": c.document.doc_code}
        for c in chunks
    ]
    hits = BM25Retriever(passages).search(q, limit)
    return [(lookup[h["passage_id"]], h["score"]) for h in hits]


def get_chunk(db: Session, chunk_id: int) -> LegalChunk | None:
    return db.scalar(select(LegalChunk).join(LegalChunk.document)
                     .options(contains_eager(LegalChunk.document)).where(LegalChunk.id == chunk_id))


def to_hit(chunk: LegalChunk) -> SourceHit:
    doc = chunk.document
    return SourceHit(
        source_id=str(chunk.id), title=doc.title, legal_identifier=doc.doc_code,
        dieu=chunk.article_number, khoan=clause_label(chunk.clause_number),
        diem=(chunk.point_letter or "").strip() or None,
        url=chunk.source_url or doc.source_url, citation_path=chunk.citation_path,
        source_page=chunk.source_page, version=doc.version,
        doc_type=doc.doc_type, hierarchy_level=chunk.hierarchy_level,
        # Trạng thái riêng của đoạn (vd 1 Khoản bị sửa đổi) ưu tiên hơn trạng thái cả văn bản;
        # chưa ai ghi trạng thái thì tính từ ngày tại hôm nay (importer không tin status của parser)
        status=next((s for s in (chunk.status, doc.status) if s and s != STATUS_UNKNOWN), None)
        or date_status(chunk.effective_date or doc.effective_date, chunk.expiry_date or doc.expiry_date, date.today()),
        effective_date=chunk.effective_date or doc.effective_date, expiry_date=chunk.expiry_date or doc.expiry_date,
        snippet=chunk.content[:SNIPPET_LEN],
    )


def to_detail(chunk: LegalChunk) -> SourceDetail:
    doc = chunk.document
    return SourceDetail(**to_hit(chunk).model_dump(), content=chunk.content, article_title=chunk.article_title,
                        issuer=doc.issuer)
