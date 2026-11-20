from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from data_pipeline.parser.chunker import _to_datetime
from data_pipeline.registry.models import LegalChunk, LegalDocument


def sync_parsed_document(
    session: Session,
    doc_metadata: Dict[str, Any],
    parsed_chunks: List[Dict[str, Any]],
) -> LegalDocument:
    """
    Đồng bộ siêu dữ liệu cấp văn bản và cấp đoạn từ parser đến cơ sở dữ liệu.
    Hỗ trợ cập nhật bản mới (Upsert) theo doc_code, tránh cột bị bỏ trống.
    """
    doc_code = doc_metadata["doc_code"]
    first_chunk = parsed_chunks[0] if parsed_chunks else {}

    eff_date = _to_datetime(doc_metadata.get("effective_date") or first_chunk.get("effective_date"))
    exp_date = _to_datetime(doc_metadata.get("expiry_date") or first_chunk.get("expiry_date"))
    issue_date = _to_datetime(doc_metadata.get("issue_date"))

    status = (
        doc_metadata.get("legal_status")
        or doc_metadata.get("status")
        or first_chunk.get("status")
        or "CHUA_XAC_DINH"
    )
    ocr_status = (
        doc_metadata.get("ocr_quality_status")
        or first_chunk.get("ocr_quality_status")
        or "RAW"
    )
    expert_status = (
        doc_metadata.get("expert_review_status")
        or first_chunk.get("expert_review_status")
        or "PENDING"
    )
    version = str(doc_metadata.get("version") or first_chunk.get("version") or "1.0")
    source_url = doc_metadata.get("source_url") or first_chunk.get("source_url")
    hierarchy_level = int(doc_metadata.get("hierarchy_level") or first_chunk.get("hierarchy_level") or 5)
    preamble = doc_metadata.get("preamble") or first_chunk.get("preamble") or ""

    pages = [c["source_page"] for c in parsed_chunks if c.get("source_page") is not None]
    total_pages = doc_metadata.get("total_pages") or (max(pages) if pages else None)

    doc = session.query(LegalDocument).filter_by(doc_code=doc_code).first()
    if doc is None:
        doc = LegalDocument(
            doc_code=doc_code,
            title=doc_metadata.get("title") or doc_code,
        )
        session.add(doc)

    doc.title = doc_metadata.get("title") or doc.title or doc_code
    doc.doc_type = doc_metadata.get("doc_type") or first_chunk.get("doc_type") or doc.doc_type or "UNKNOWN"
    doc.hierarchy_level = hierarchy_level
    doc.preamble = preamble or doc.preamble
    doc.issuer = doc_metadata.get("issuer") or doc.issuer
    doc.source_url = source_url or doc.source_url
    doc.total_pages = total_pages or doc.total_pages
    doc.issue_date = issue_date or doc.issue_date
    doc.effective_date = eff_date if eff_date is not None else doc.effective_date
    doc.expiry_date = exp_date if exp_date is not None else doc.expiry_date
    doc.status = status
    doc.ocr_quality_status = ocr_status
    doc.expert_review_status = expert_status
    doc.version = version
    doc.amends_doc_code = (
        doc_metadata.get("amends_doc_code")
        or first_chunk.get("amends_doc_code")
        or doc.amends_doc_code
    )
    doc.replaces_doc_code = (
        doc_metadata.get("replaces_doc_code")
        or first_chunk.get("replaces_doc_code")
        or doc.replaces_doc_code
    )
    doc.updated_at = datetime.now(timezone.utc)

    session.flush()

    session.query(LegalChunk).filter_by(doc_id=doc.id).delete()

    for item in parsed_chunks:
        chunk_eff = _to_datetime(item.get("effective_date")) or eff_date
        chunk = LegalChunk(
            doc_id=doc.id,
            article_number=str(item.get("article_number", "0")),
            article_title=item.get("article_title"),
            article_intro=item.get("article_intro"),
            clause_number=str(item.get("clause_number", "0")),
            clause_intro=item.get("clause_intro"),
            point_letter=item.get("point_letter", ""),
            citation_path=item.get("citation_path") or doc_code,
            content=item["content"],
            source_page=item.get("source_page"),
            source_url=item.get("source_url") or source_url,
            hierarchy_level=int(item.get("hierarchy_level") or hierarchy_level),
            effective_date=chunk_eff,
            status=item.get("status") or status,
            ocr_quality_status=item.get("ocr_quality_status") or ocr_status,
            expert_review_status=item.get("expert_review_status") or expert_status,
            version=str(item.get("version") or version),
        )
        session.add(chunk)

    session.commit()
    session.refresh(doc)
    return doc