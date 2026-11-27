"""
tests/test_ocr_review_status.py  –  IMPORTER NHẬN METADATA MỚI CỦA PARSER (SCRUM-30 của Duyên)
==============================================================================================
Parser xuất thêm preamble, ocr_quality_status, expert_review_status cho mỗi đoạn.
Importer phải lưu đủ (không để "model có cột nhưng dữ liệu không được lưu") và không nhận phê duyệt qua file nạp.
"""
import pytest
from pydantic import ValidationError

from app.core.database import SessionLocal
from app.models import LegalChunk, LegalDocument
from app.services.legal_ingestion_service import ingest_legal_document
from data_pipeline.parser.chunker import chunk_legal_document

TEXT = """Căn cứ Luật Quản lý thuế số 38/2019/QH14;
Chính phủ ban hành Nghị định mẫu.

Điều 1. Phạm vi điều chỉnh
1. Nghị định này quy định về hóa đơn.
2. Áp dụng với người nộp thuế.
"""
DOC = {"doc_code": "OCR-01", "title": "Nghị định mẫu", "doc_type": "NGHI_DINH", "hierarchy_level": 2,
       "effective_date": "2025-01-01"}


def _payload(**meta):
    chunks = chunk_legal_document(TEXT, DOC["doc_code"], 2, 1, {"doc_type": "NGHI_DINH", **meta})
    return {"document": dict(DOC), "chunks": chunks, "tax_types": ["VAT"], "as_of": "2026-11-20"}


def test_luu_preamble_va_trang_thai_ocr_tu_parser(client):
    payload = _payload(ocr_quality_status="VERIFIED")
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    with SessionLocal() as db:
        doc = db.get(LegalDocument, receipt.document_id)
        assert doc.preamble.startswith("Căn cứ Luật Quản lý thuế")      # gom từ các đoạn về văn bản
        assert (doc.ocr_quality_status, doc.expert_review_status) == ("RAW", "PENDING")
        chunks = [db.get(LegalChunk, i) for i in receipt.chunk_ids]
        assert {(c.ocr_quality_status, c.expert_review_status) for c in chunks} == {("VERIFIED", "PENDING")}


def test_khong_nhan_phe_duyet_qua_file_nap(client):
    with pytest.raises(ValidationError, match="chỉ nhận PENDING"):
        ingest_legal_document(None, _payload(expert_review_status="APPROVED"))


def test_preamble_cac_doan_phai_khop_van_ban(client):
    payload = _payload()
    payload["document"]["preamble"] = "Căn cứ khác"
    with pytest.raises(ValidationError, match="preamble"):
        ingest_legal_document(None, payload)


def test_trang_thai_ocr_ngoai_danh_sach_bi_tu_choi(client):
    with pytest.raises(ValidationError):
        ingest_legal_document(None, _payload(ocr_quality_status="GOOD"))


# Cột chưa lưu từ file nạp, có lý do: khóa/thời điểm do hệ thống sinh; `status` pháp lý chờ thống nhất (xem HUONG_DAN_TEST)
NOT_FROM_FILE = {"id", "doc_id", "created_at", "updated_at", "status"}


def test_moi_cot_metadata_trong_model_deu_duoc_luu(client):
    """SCRUM-36: tránh "model có cột nhưng dữ liệu không được lưu" – file nạp đủ trường thì mọi cột đều có giá trị."""
    payload = _payload(ocr_quality_status="VERIFIED", source_url="https://vbpl.vn/ocr-01", version="2.0",
                       effective_date="2025-01-01")
    payload["document"].update(issuer="Chính phủ", source_url="https://vbpl.vn/ocr-01", total_pages=5,
                               issue_date="2024-12-01", expiry_date="2030-01-01", version="2.0",
                               amends_doc_code="OCR-00", replaces_doc_code="OCR-OLD")
    for c in payload["chunks"]:
        c.update(article_title=c.get("article_title") or "Phạm vi", article_intro="Mở đầu Điều",
                 clause_intro="Mở đầu Khoản", point_letter="a", source_page=2,
                 source_url="https://vbpl.vn/ocr-01#page=2", effective_date="2025-01-01")
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    with SessionLocal() as db:
        chunk = db.get(LegalChunk, receipt.chunk_ids[0])
        for row in (chunk.document, chunk):
            empty = [c.name for c in row.__table__.columns
                     if c.name not in NOT_FROM_FILE and getattr(row, c.name) in (None, "")]
            assert not empty, f"{row.__tablename__} không lưu: {empty}"
        assert chunk.version == "2.0" and chunk.source_page == 2
