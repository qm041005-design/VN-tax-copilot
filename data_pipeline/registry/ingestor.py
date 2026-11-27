from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session

from data_pipeline.parser.chunker import _to_datetime, chunk_ocr_pages
from data_pipeline.registry.hierarchy import get_hierarchy_level, normalize_doc_type
from data_pipeline.registry.models import LegalChunk, LegalDocument
from data_pipeline.registry.repository import normalize_tax_types, sync_parsed_document


def build_stable_chunk_id(
    doc_code: str,
    article_number: str,
    clause_number: str,
    point_letter: str = "",
) -> str:
    """Tạo ID ổn định (deterministic) dựa trên số hiệu văn bản và tọa độ Điều/Khoản/Điểm."""
    code = str(doc_code).strip().upper()
    art = str(article_number or "0").strip().lower()
    clause = str(clause_number or "0").strip().lower()
    point = str(point_letter or "0").strip().lower()
    return f"{code}::D{art}::K{clause}::P{point}"


def normalize_doc_metadata(
    raw_meta: Dict[str, Any],
    strict: bool = False,
) -> Dict[str, Any]:
    """Chuẩn hóa và xác thực siêu dữ liệu văn bản pháp luật trước khi nạp registry."""
    doc_code = str(raw_meta.get("doc_code") or "").strip()
    if not doc_code:
        raise ValueError("Thiếu trường bắt buộc 'doc_code' trong metadata.")

    eff_date = _to_datetime(raw_meta.get("effective_date"))
    exp_date = _to_datetime(raw_meta.get("expiry_date"))
    if eff_date and exp_date and exp_date < eff_date:
        raise ValueError(
            "Ngày hết hiệu lực (expiry_date) không được nhỏ hơn ngày có hiệu lực (effective_date)."
        )

    raw_url = raw_meta.get("source_url")
    source_url = str(raw_url).strip() if raw_url is not None else ""
    if source_url and not source_url.lower().startswith("https://"):
        raise ValueError(
            "Trường 'source_url' phải là đường dẫn hợp lệ bắt đầu bằng 'https://'."
        )

    tax_types = normalize_tax_types(raw_meta.get("tax_types"))

    if strict:
        if eff_date is None:
            raise ValueError("Chế độ strict: thiếu hoặc sai định dạng 'effective_date'.")
        if not source_url:
            raise ValueError("Chế độ strict: thiếu đường dẫn nguồn 'source_url' (https://).")
        if not tax_types:
            raise ValueError("Chế độ strict: thiếu loại thuế 'tax_types' (VD: ['VAT', 'TNDN']).")

    doc_type = normalize_doc_type(raw_meta.get("doc_type"))
    hierarchy_level = raw_meta.get("hierarchy_level") or get_hierarchy_level(doc_type)

    normalized = dict(raw_meta)
    normalized.update(
        {
            "doc_code": doc_code,
            "title": str(raw_meta.get("title") or doc_code).strip(),
            "doc_type": doc_type,
            "hierarchy_level": int(hierarchy_level),
            "source_url": source_url or None,
            "tax_types": tax_types,
            "as_of": raw_meta.get("as_of") or datetime.now(timezone.utc).replace(tzinfo=None),
            "version": str(raw_meta.get("version") or "1.0").strip(),
            "ocr_quality_status": str(raw_meta.get("ocr_quality_status") or "RAW").strip().upper(),
            "expert_review_status": str(raw_meta.get("expert_review_status") or "PENDING").strip().upper(),
        }
    )

    return normalized


def ingest_ocr_document(
    session: Session,
    ocr_pages: List[Dict[str, Any]],
    raw_meta: Dict[str, Any],
    strict: bool = False,
) -> LegalDocument:
    """Chuẩn hóa metadata, xác thực đầu vào, cắt chunk đa trang OCR và đồng bộ (Upsert) vào Registry."""
    if not isinstance(ocr_pages, list) or not ocr_pages:
        raise ValueError("Danh sách 'ocr_pages' không được rỗng.")

    for page_item in ocr_pages:
        page_val = page_item.get("page") if isinstance(page_item, dict) else None
        if (
            page_val is None
            or isinstance(page_val, bool)
            or not str(page_val).strip().isdigit()
            or int(page_val) <= 0
        ):
            raise ValueError(
                "Mỗi trang OCR phải có số trang PDF hợp lệ ('source_page' / 'page' là số nguyên dương)."
            )

    clean_meta = normalize_doc_metadata(raw_meta, strict=strict)
    parsed_chunks = chunk_ocr_pages(
        pages=ocr_pages,
        doc_code=clean_meta["doc_code"],
        hierarchy_level=clean_meta["hierarchy_level"],
        metadata=clean_meta,
    )
    if not parsed_chunks:
        raise ValueError(
            f"Không trích xuất được điều khoản hợp lệ nào cho văn bản '{clean_meta['doc_code']}'."
        )

    return sync_parsed_document(
        session=session,
        doc_metadata=clean_meta,
        parsed_chunks=parsed_chunks,
    )


def ingest_from_json(
    session: Session,
    json_path: str | Path,
    strict: bool = False,
) -> LegalDocument:
    """Đọc file JSON (gồm 'metadata' và 'ocr_pages') và nạp trực tiếp vào Registry."""
    path = Path(json_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "metadata" not in data or "ocr_pages" not in data:
        raise ValueError(
            "File JSON không hợp lệ: cần có đủ 2 khóa 'metadata' và 'ocr_pages'."
        )

    return ingest_ocr_document(
        session=session,
        ocr_pages=data["ocr_pages"],
        raw_meta=data["metadata"],
        strict=strict,
    )


def audit_document_chunks(doc: LegalDocument, chunks: List[LegalChunk]) -> List[Dict[str, Any]]:
    """Kiểm tra tính ổn định của ID và lập danh sách đoạn thiếu hoặc lỗi trong một văn bản."""
    issues: List[Dict[str, Any]] = []

    if doc.ocr_quality_status != "VERIFIED":
        issues.append(
            {
                "doc_code": doc.doc_code,
                "issue_type": "UNVERIFIED_OCR",
                "detail": f"Trạng thái OCR hiện là '{doc.ocr_quality_status}', chưa hiệu đính (VERIFIED).",
            }
        )

    if doc.effective_date is None:
        issues.append(
            {
                "doc_code": doc.doc_code,
                "issue_type": "MISSING_EFFECTIVE_DATE",
                "detail": "Thiếu ngày có hiệu lực (effective_date).",
            }
        )

    if not doc.source_url or not str(doc.source_url).lower().startswith("https://"):
        issues.append(
            {
                "doc_code": doc.doc_code,
                "issue_type": "MISSING_OR_INVALID_SOURCE_URL",
                "detail": "Thiếu đường dẫn nguồn 'source_url' hoặc không bắt đầu bằng 'https://'.",
            }
        )

    if not doc.tax_types:
        issues.append(
            {
                "doc_code": doc.doc_code,
                "issue_type": "MISSING_TAX_TYPES",
                "detail": "Thiếu danh sách loại thuế áp dụng ('tax_types').",
            }
        )

    seen_ids: set[str] = set()
    article_nums: set[int] = set()

    for chunk in chunks:
        stable_id = build_stable_chunk_id(
            doc.doc_code, chunk.article_number, chunk.clause_number, chunk.point_letter
        )

        if stable_id in seen_ids:
            issues.append(
                {
                    "doc_code": doc.doc_code,
                    "stable_id": stable_id,
                    "issue_type": "DUPLICATE_STABLE_ID",
                    "detail": f"Trùng tọa độ đoạn '{stable_id}' (citation: {chunk.citation_path}).",
                }
            )
        seen_ids.add(stable_id)

        if chunk.source_page is None:
            issues.append(
                {
                    "doc_code": doc.doc_code,
                    "stable_id": stable_id,
                    "issue_type": "MISSING_SOURCE_PAGE",
                    "detail": f"Đoạn '{chunk.citation_path}' bị thiếu số trang nguồn (source_page).",
                }
            )

        if not chunk.content or len(chunk.content.strip()) < 10:
            issues.append(
                {
                    "doc_code": doc.doc_code,
                    "stable_id": stable_id,
                    "issue_type": "EMPTY_OR_SHORT_CONTENT",
                    "detail": f"Đoạn '{chunk.citation_path}' có nội dung rỗng hoặc quá ngắn.",
                }
            )

        match = re.match(r"^(\d+)", str(chunk.article_number or ""))
        if match:
            art_num = int(match.group(1))
            if art_num > 0:
                article_nums.add(art_num)

    if len(article_nums) >= 2:
        sorted_nums = sorted(article_nums)
        expected = set(range(sorted_nums[0], sorted_nums[-1] + 1))
        missing_articles = sorted(expected - article_nums)
        if missing_articles:
            issues.append(
                {
                    "doc_code": doc.doc_code,
                    "issue_type": "MISSING_ARTICLE_SEQUENCE",
                    "detail": f"Phát hiện thiếu Điều số: {missing_articles}.",
                    "missing_articles": missing_articles,
                }
            )

    return issues


def _iso_or_none(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def ingest_batch_with_snapshot(
    session: Session,
    batch_dir: str | Path,
    output_dir: str | Path,
    snapshot_version: str,
    strict: bool = False,
) -> Tuple[Path, Path, Dict[str, Any]]:
    """
    Nạp dữ liệu OCR theo từng đợt từ thư mục JSON, xuất:
    1. File snapshot có phiên bản kèm stable_id (phục vụ tích hợp đánh chỉ mục).
    2. File báo cáo danh sách văn bản lỗi và các đoạn thiếu/lỗi.
    """
    batch_path = Path(batch_dir)
    if not batch_path.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục đợt nạp: '{batch_path}'.")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_files = sorted(batch_path.glob("*.json"))
    snapshot_docs: List[Dict[str, Any]] = []
    failed_documents: List[Dict[str, Any]] = []
    segment_issues: List[Dict[str, Any]] = []
    total_chunks = 0

    for file_path in json_files:
        try:
            doc = ingest_from_json(session, file_path, strict=strict)
            chunks = (
                session.query(LegalChunk)
                .filter_by(doc_id=doc.id)
                .order_by(LegalChunk.id.asc())
                .all()
            )
            doc_issues = audit_document_chunks(doc, chunks)
            segment_issues.extend(doc_issues)

            serialized_chunks = []
            for c in chunks:
                stable_id = build_stable_chunk_id(
                    doc.doc_code, c.article_number, c.clause_number, c.point_letter
                )
                serialized_chunks.append(
                    {
                        "stable_id": stable_id,
                        "article_number": c.article_number,
                        "clause_number": c.clause_number,
                        "point_letter": c.point_letter,
                        "citation_path": c.citation_path,
                        "content": c.content,
                        "source_page": c.source_page,
                        "source_url": c.source_url,
                        "tax_types": c.tax_types or [],
                        "effective_date": _iso_or_none(c.effective_date),
                        "expiry_date": _iso_or_none(c.expiry_date),
                        "status": c.status,
                        "version": c.version,
                    }
                )

            total_chunks += len(serialized_chunks)
            snapshot_docs.append(
                {
                    "source_file": file_path.name,
                    "doc_code": doc.doc_code,
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "hierarchy_level": doc.hierarchy_level,
                    "source_url": doc.source_url,
                    "total_pages": doc.total_pages,
                    "tax_types": doc.tax_types or [],
                    "effective_date": _iso_or_none(doc.effective_date),
                    "expiry_date": _iso_or_none(doc.expiry_date),
                    "status": doc.status,
                    "ocr_quality_status": doc.ocr_quality_status,
                    "expert_review_status": doc.expert_review_status,
                    "version": doc.version,
                    "chunks": serialized_chunks,
                }
            )
        except Exception as exc:
            session.rollback()
            failed_documents.append(
                {
                    "source_file": file_path.name,
                    "error": str(exc),
                }
            )

    summary = {
        "snapshot_version": snapshot_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(json_files),
        "ingested_documents": len(snapshot_docs),
        "failed_documents": len(failed_documents),
        "total_chunks": total_chunks,
        "total_segment_issues": len(segment_issues),
    }

    snapshot_payload = {
        "summary": summary,
        "documents": snapshot_docs,
    }
    issues_payload = {
        "snapshot_version": snapshot_version,
        "created_at": summary["created_at"],
        "failed_documents": failed_documents,
        "segment_issues": segment_issues,
    }

    snapshot_file = out_path / f"snapshot_{snapshot_version}.json"
    issues_file = out_path / f"issues_{snapshot_version}.json"

    snapshot_file.write_text(
        json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    issues_file.write_text(
        json.dumps(issues_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return snapshot_file, issues_file, summary