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
