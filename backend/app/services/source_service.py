"""
app/services/source_service.py  –  TÌM KIẾM & XEM NGUỒN LUẬT (đọc bảng legal_documents / legal_chunks)
=====================================================================================================
Văn bản pháp luật là dữ liệu CÔNG KHAI, dùng chung mọi tenant -> không lọc theo tenant_id
(nhưng endpoint vẫn bắt đăng nhập).
"""
import re
from datetime import date, datetime, time

from sqlalchemy import case, select
from sqlalchemy.orm import Session, contains_eager

from app.models import LegalChunk, LegalDocument
from app.models.legal_source import STATUS_UNKNOWN
from app.schemas.source import SourceDetail, SourceHit

MAX_TERMS = 20
SNIPPET_LEN = 300


def _like(term: str) -> str:
    """Escape ký tự đặc biệt của LIKE để từ khóa '%' hay '_' không thành wildcard."""
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _terms(q: str) -> list[str]:
    """Tách câu hỏi thành từ (bỏ dấu câu, trùng lặp), tối đa MAX_TERMS từ."""
    return list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", q)))[:MAX_TERMS]


def search(db: Session, q: str, doc_type: str | None = None, as_of: date | None = None,
           limit: int = 10) -> list[tuple[LegalChunk, int]]:
    """
    Tìm đoạn luật chứa nhiều từ khóa nhất. Trả [(chunk, số_từ_khớp)], xếp theo:
      số từ khớp giảm dần -> thứ bậc văn bản (Luật trước Công văn) -> văn bản hiệu lực mới hơn trước.
    as_of: chỉ lấy văn bản đã có hiệu lực và chưa hết hiệu lực tại ngày đó (RES 01).
    """
    # shortcut: tìm từ khóa bằng ILIKE, chưa có BM25/vector; thay bằng Hybrid Retrieval của nhóm 6 khi có.
    terms = _terms(q)
    if not terms:
        return []
    score = sum(case((LegalChunk.content.ilike(_like(t), escape="\\"), 1), else_=0) for t in terms)
    stmt = (select(LegalChunk, score.label("score"))
            .join(LegalChunk.document).options(contains_eager(LegalChunk.document))
            .where(score > 0))
    if doc_type:
        stmt = stmt.where(LegalDocument.doc_type == doc_type.upper())
    if as_of:
        day = datetime.combine(as_of, time.min)
        stmt = stmt.where((LegalDocument.effective_date.is_(None)) | (LegalDocument.effective_date <= day),
                          (LegalDocument.expiry_date.is_(None)) | (LegalDocument.expiry_date > day))
    stmt = stmt.order_by(score.desc(), LegalChunk.hierarchy_level, LegalDocument.effective_date.desc(),
                         LegalChunk.id).limit(limit)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_chunk(db: Session, chunk_id: int) -> LegalChunk | None:
    return db.scalar(select(LegalChunk).join(LegalChunk.document)
                     .options(contains_eager(LegalChunk.document)).where(LegalChunk.id == chunk_id))


def to_hit(chunk: LegalChunk) -> SourceHit:
    doc = chunk.document
    return SourceHit(
        source_id=str(chunk.id), title=doc.title, legal_identifier=doc.doc_code,
        # clause_number là chuỗi ("1", "2a"); "0" hoặc rỗng = đoạn không thuộc Khoản nào
        dieu=chunk.article_number, khoan=chunk.clause_number if chunk.clause_number not in (None, "", "0") else None,
        diem=chunk.point_letter or None, url=chunk.source_url or doc.source_url, citation_path=chunk.citation_path,
        doc_type=doc.doc_type, hierarchy_level=chunk.hierarchy_level,
        # Trạng thái riêng của đoạn (vd 1 Khoản bị sửa đổi) ưu tiên hơn trạng thái cả văn bản
        status=chunk.status if chunk.status and chunk.status != STATUS_UNKNOWN else doc.status or STATUS_UNKNOWN,
        effective_date=chunk.effective_date or doc.effective_date, expiry_date=doc.expiry_date,
        snippet=chunk.content[:SNIPPET_LEN],
    )


def to_detail(chunk: LegalChunk) -> SourceDetail:
    doc = chunk.document
    return SourceDetail(**to_hit(chunk).model_dump(), content=chunk.content, article_title=chunk.article_title,
                        issuer=doc.issuer, version=doc.version, source_page=chunk.source_page)
