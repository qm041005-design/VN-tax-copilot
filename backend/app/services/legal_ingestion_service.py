"""Internal, append-only import of authorized public-law parser output.

No public ingestion endpoint; caller controls access, source rights and outer
transaction. Never overwrite document/chunk IDs already used by citations.
"""
from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LegalDocument, LegalChunk, LegalDocumentTaxScope
from app.schemas.ingestion import ImportInput


@dataclass(frozen=True)
class ImportReceipt:
    document_id: int
    chunk_ids: tuple[int, ...]
    temporal_status: str
    warnings: tuple[str, ...]


def temporal_status(document, as_of):
    """Date classification only, not expert validation of legal applicability."""
    if document.expiry_date is not None and as_of >= document.expiry_date:
        return "HET_HIEU_LUC"
    if document.effective_date is None or as_of < document.effective_date:
        return "CHUA_XAC_DINH"
    return "CON_HIEU_LUC"


def ingest_legal_document(db: Session, payload: dict) -> ImportReceipt:
    """Validate the entire batch BEFORE writes; flush in the caller transaction, never commit.

    Use a dedicated Session/transaction. Caller may commit the result or roll
    back. Duplicate doc_code is rejected instead of replacing cited content.
    """
    data = ImportInput.model_validate(payload)
    fields = data.document.model_dump()
    for key in ("issue_date", "effective_date", "expiry_date"):
        if fields[key] is not None:
            fields[key] = datetime.combine(fields[key], time.min)
    if db.scalar(select(LegalDocument.id).where(LegalDocument.doc_code == data.document.doc_code)):
        raise ValueError("Mã văn bản đã tồn tại; không ghi đè phiên bản đang được trích dẫn.")
    doc = LegalDocument(**fields)
    db.add(doc)
    db.flush()
    rows = []
    for chunk in data.chunks:
        chunk_start = datetime.combine(chunk.effective_date, time.min) if chunk.effective_date else None
        row = LegalChunk(doc_id=doc.id, article_number=chunk.article_number,
                         article_title=chunk.article_title, article_intro=chunk.article_intro,
                         clause_number=chunk.clause_number or "0", clause_intro=chunk.clause_intro,
                         point_letter=chunk.point_letter or "",
                         citation_path=chunk.citation_path, content=chunk.content,
                         source_page=chunk.source_page, source_url=chunk.source_url,
                         hierarchy_level=chunk.hierarchy_level, effective_date=chunk_start,
                         version=doc.version)
        db.add(row)
        rows.append(row)
    for chunk, row in zip(data.chunks, rows):  # SCRUM-30: trạng thái OCR/duyệt của từng đoạn
        row.ocr_quality_status = chunk.ocr_quality_status or data.document.ocr_quality_status
        row.expert_review_status = "PENDING"
    for tax_type in sorted(set(data.tax_types)):
        db.add(LegalDocumentTaxScope(doc_id=doc.id, tax_type=tax_type))
    db.flush()
    receipt = ImportReceipt(doc.id, tuple(row.id for row in rows),
                            temporal_status(data.document, data.as_of),
                            ("Trạng thái chỉ suy ra từ ngày; chưa xác minh pháp lý hoặc tính áp dụng.",
                             "status do parser gửi không được dùng để ghi nhận phê duyệt."))
    return receipt
