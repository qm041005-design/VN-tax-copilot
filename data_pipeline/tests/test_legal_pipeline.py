import pytest
from datetime import datetime

from data_pipeline.registry.hierarchy import get_hierarchy_level, normalize_doc_type
from data_pipeline.parser.chunker import chunk_legal_document

try:
    from data_pipeline.registry.models import (
        LegalDocument,
        LegalChunk,
        LegalDocumentAmendment,
    )
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


@pytest.mark.parametrize("doc_type, expected_level", [
    ("LUAT", 1),
    ("Luật", 1),
    ("Bộ luật", 1),
    ("BO_LUAT", 1),
    ("NGHI_DINH", 2),
    ("Nghị định", 2),
    ("nghi_dinh", 2),
    ("THONG_TU", 3),
    ("Thông tư", 3),
    ("thong_tu", 3),
    ("CONG_VAN", 4),
    ("Công văn", 4),
    ("cong_van", 4),
])
def test_hierarchy_valid_types(doc_type, expected_level):
    """Nhận diện chính xác cả 4 cấp bậc pháp lý bất kể viết hoa/thường hay dấu gạch dưới."""
    assert get_hierarchy_level(doc_type) == expected_level


@pytest.mark.parametrize("unknown_type", ["UNKNOWN", "BAO_CAO", "QUYET_DINH", "", "   ", None])
def test_hierarchy_unknown_types_handled_gracefully(unknown_type):
    """Xử lý loại văn bản chưa xác định về UNKNOWN (cấp 5) thay vì ném lỗi."""
    assert normalize_doc_type(unknown_type) == "UNKNOWN"
    assert get_hierarchy_level(unknown_type) == 5


def test_chunker_alphanumeric_article_and_article_intro():
    """Bắt chuẩn Điều có chữ cái (Điều 1a, 14b) và giữ trọn câu dẫn mở đầu Điều."""
    text = """
Điều 1a. Phạm vi điều chỉnh bổ sung
Nghị định này quy định chi tiết thi hành một số điều của Luật Quản lý thuế bao gồm:
a) Khai thuế, tính thuế, ấn định thuế;
b) Hoàn thuế, miễn thuế, giảm thuế;
đ) Quản lý thông tin người nộp thuế.
"""
    chunks = chunk_legal_document(text, "126/2020/NĐ-CP", hierarchy_level=2, source_page=5)

    assert len(chunks) == 3
    assert chunks[0]["article_number"] == "1a"
    assert chunks[0]["clause_number"] == "0"
    assert chunks[0]["point_letter"] == "a"
    assert chunks[0]["status"] == "CHUA_XAC_DINH"
    assert "Nghị định này quy định chi tiết thi hành" in chunks[0]["article_intro"]
    assert "Nghị định này quy định chi tiết thi hành" in chunks[0]["content"]
    assert chunks[2]["point_letter"] == "đ"
    assert chunks[2]["source_page"] == 5


def test_chunker_clause_lead_in_preserved_across_points():
    """Giữ nguyên câu dẫn mở đầu Khoản khi bóc tách xuống các điểm a, b."""
    text = """
Điều 16. Quyền của người nộp thuế
1. Được hướng dẫn giải thích khi có yêu cầu.
2. Được nhận văn bản liên quan đến việc kiểm tra thuế bao gồm:
a) Quyết định kiểm tra thuế;
b) Biên bản kiểm tra thuế.
"""
    chunks = chunk_legal_document(text, "38/2019/QH14", hierarchy_level=1, source_page=10)

    assert len(chunks) == 3
    assert chunks[0]["clause_number"] == "1"
    assert chunks[1]["clause_number"] == "2"
    assert chunks[1]["point_letter"] == "a"
    assert "Được nhận văn bản liên quan" in chunks[1]["clause_intro"]
    assert "Được nhận văn bản liên quan" in chunks[1]["content"]
    assert "Được nhận văn bản liên quan" in chunks[2]["content"]


def test_chunker_multi_articles_mixed_structure():
    """Kiểm tra văn bản nhiều Điều liên tiếp và giữ nguyên chữ cái trong số Khoản (1a)."""
    text = """
Điều 1. Phạm vi điều chỉnh
Luật này quy định việc quản lý các loại thuế.

Điều 1a. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Người nộp thuế là tổ chức, hộ gia đình, cá nhân nộp thuế.
1a. Cơ quan quản lý thuế gồm cơ quan thuế và cơ quan hải quan.
"""
    chunks = chunk_legal_document(text, "38/2019/QH14", hierarchy_level=1, source_page=1)

    assert len(chunks) == 3
    assert chunks[0]["article_number"] == "1"
    assert chunks[0]["clause_number"] == "0"
    assert chunks[1]["article_number"] == "1a"
    assert chunks[1]["clause_number"] == "1"
    assert "Trong Luật này, các từ ngữ dưới đây" in chunks[1]["content"]
    assert chunks[2]["clause_number"] == "1a"
    assert "Khoản 1a, Điều 1a" in chunks[2]["citation_path"]


def test_chunker_empty_or_unstructured_text():
    """Đảm bảo không crash khi gặp văn bản rỗng hoặc chưa có cấu trúc Điều."""
    assert chunk_legal_document("", "38/2019/QH14", hierarchy_level=1) == []
    assert chunk_legal_document("Văn bản chỉ có tiêu đề chung", "38/2019/QH14", hierarchy_level=1) == []


def test_chunker_enriched_metadata():
    """Kiểm tra bổ sung nguồn, trang, hiệu lực, phiên bản và trạng thái mặc định khi thiếu ngày hiệu lực."""
    text = """
Điều 2. Đối tượng áp dụng
Áp dụng đối với doanh nghiệp hoạt động tại Việt Nam.
"""
    
    chunks_no_date = chunk_legal_document(text, "99/2025/NĐ-CP", hierarchy_level=2, source_page=3)
    assert chunks_no_date[0]["status"] == "CHUA_XAC_DINH"

    
    eff_date = datetime(2026, 1, 1)
    meta = {
        "doc_type": "NGHI_DINH",
        "source_url": "https://vanban.chinhphu.vn/test",
        "effective_date": eff_date,
        "status": "SUA_DOI_BO_SUNG",
        "version": "2.0",
        "amends_doc_code": "126/2020/NĐ-CP",
        "replaces_doc_code": "83/2013/NĐ-CP",
    }
    chunks = chunk_legal_document(text, "99/2025/NĐ-CP", hierarchy_level=2, source_page=3, metadata=meta)

    assert len(chunks) == 1
    c = chunks[0]
    assert c["source_page"] == 3
    assert c["source_url"] == "https://vanban.chinhphu.vn/test"
    assert c["effective_date"] == eff_date
    assert c["status"] == "SUA_DOI_BO_SUNG"
    assert c["version"] == "2.0"
    assert c["amends_doc_code"] == "126/2020/NĐ-CP"
    assert c["replaces_doc_code"] == "83/2013/NĐ-CP"


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_models_schema_columns_and_metadata():
    """Kiểm tra các cột metadata mới và kiểu chuỗi của clause_number trên SQLAlchemy models."""
    doc_cols = set(LegalDocument.__table__.columns.keys())
    chunk_cols = set(LegalChunk.__table__.columns.keys())
    amend_cols = set(LegalDocumentAmendment.__table__.columns.keys())

    assert {"source_url", "total_pages", "effective_date", "expiry_date", "status", "version", "amends_doc_code", "replaces_doc_code"}.issubset(doc_cols)
    assert {"article_intro", "clause_intro", "source_page", "source_url", "effective_date", "status", "version"}.issubset(chunk_cols)
    assert {"original_doc_id", "amending_doc_id", "amendment_type", "effective_date"}.issubset(amend_cols)
    assert LegalChunk.__table__.columns["clause_number"].type.python_type is str
    assert LegalDocument.__table__.columns["status"].default.arg == "CHUA_XAC_DINH"