import ast
import re
from pathlib import Path
from datetime import datetime
import pytest

from data_pipeline.registry.hierarchy import get_hierarchy_level
from data_pipeline.parser.chunker import chunk_legal_document

# Kiểm tra môi trường hiện tại có tải được DLL của SQLAlchemy hay không
try:
    from data_pipeline.registry.models import LegalDocument, LegalChunk, LegalDocumentAmendment
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


@pytest.mark.parametrize("invalid_type", ["UNKNOWN", "BAO_CAO", "QUYET_DINH", "", "   ", None])
def test_hierarchy_invalid_types_raise_error(invalid_type):
    """Từ chối loại văn bản không hợp lệ bằng ValueError thay vì gán mặc định thành Công văn."""
    with pytest.raises(ValueError):
        get_hierarchy_level(invalid_type)




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
    assert chunks[0]["clause_number"] == 0
    assert chunks[0]["point_letter"] == "a"
    assert chunks[0]["source_page"] == 5
    assert "Nghị định này quy định chi tiết thi hành một số điều của Luật Quản lý thuế bao gồm:" in chunks[0]["content"]
    assert chunks[0]["citation_path"] == "Điểm a, Điều 1a, 126/2020/NĐ-CP"
    assert chunks[2]["point_letter"] == "đ"


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
    assert chunks[0]["clause_number"] == 1
    assert chunks[0]["point_letter"] == ""
    assert chunks[0]["citation_path"] == "Khoản 1, Điều 16, 38/2019/QH14"

    assert chunks[1]["point_letter"] == "a"
    assert "Được nhận văn bản liên quan đến việc kiểm tra thuế bao gồm: Quyết định kiểm tra thuế;" in chunks[1]["content"]

    assert chunks[2]["point_letter"] == "b"
    assert "Được nhận văn bản liên quan đến việc kiểm tra thuế bao gồm: Biên bản kiểm tra thuế." in chunks[2]["content"]


def test_chunker_multi_articles_mixed_structure():
    """Kiểm tra văn bản nhiều Điều liên tiếp có cấu trúc hỗn hợp."""
    text = """
Điều 1. Phạm vi điều chỉnh
Luật này quy định việc quản lý các loại thuế.

Điều 1a. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Người nộp thuế là tổ chức, hộ gia đình, cá nhân nộp thuế.
2. Cơ quan quản lý thuế gồm cơ quan thuế và cơ quan hải quan.
"""
    chunks = chunk_legal_document(text, "38/2019/QH14", hierarchy_level=1, source_page=1)

    assert len(chunks) == 3
    assert chunks[0]["article_number"] == "1"
    assert chunks[0]["clause_number"] == 0
    assert chunks[1]["article_number"] == "1a"
    assert chunks[1]["clause_number"] == 1
    assert "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:" in chunks[1]["content"]
    assert chunks[2]["clause_number"] == 2


def test_chunker_empty_or_unstructured_text():
    """Đảm bảo không crash khi gặp văn bản rỗng hoặc chưa có cấu trúc Điều."""
    assert chunk_legal_document("", "38/2019/QH14", hierarchy_level=1) == []
    assert chunk_legal_document("Văn bản chỉ có tiêu đề chung", "38/2019/QH14", hierarchy_level=1) == []




def test_models_schema_columns_and_metadata():
    """Kiểm tra schema 3 bảng LegalDocument, LegalChunk, LegalDocumentAmendment và kiểu String cho số Điều."""
    expected_doc_cols = {
        "id", "doc_code", "title", "doc_type", "hierarchy_level",
        "issuer", "source_url", "issue_date", "effective_date",
        "expiry_date", "version", "created_at"
    }
    expected_chunk_cols = {
        "id", "doc_id", "article_number", "article_title",
        "clause_number", "point_letter", "citation_path",
        "content", "source_page", "hierarchy_level"
    }
    expected_amendment_cols = {
        "id", "original_doc_id", "amending_doc_id",
        "amendment_type", "description", "created_at"
    }

    if HAS_SQLALCHEMY:
        doc_columns = set(LegalDocument.__table__.columns.keys())
        assert expected_doc_cols.issubset(doc_columns)

        chunk_columns = set(LegalChunk.__table__.columns.keys())
        assert expected_chunk_cols.issubset(chunk_columns)

        amendment_columns = set(LegalDocumentAmendment.__table__.columns.keys())
        assert expected_amendment_cols.issubset(amendment_columns)

        article_col_type = str(LegalChunk.__table__.columns["article_number"].type)
        assert "VARCHAR" in article_col_type.upper() or "CHAR" in article_col_type.upper()

        doc = LegalDocument(
            doc_code="126/2020/NĐ-CP",
            title="Nghị định quy định chi tiết Luật Quản lý thuế",
            doc_type="NGHI_DINH",
            hierarchy_level=2,
            issuer="Chính phủ",
            source_url="https://vanban.chinhphu.vn/126-2020-nd-cp",
            issue_date=datetime(2020, 10, 19),
            effective_date=datetime(2020, 12, 5),
            expiry_date=None,
            version="1.0"
        )
        chunk = LegalChunk(
            article_number="1a",
            article_title="Phạm vi điều chỉnh bổ sung",
            clause_number=1,
            point_letter="a",
            citation_path="Điểm a, Khoản 1, Điều 1a, 126/2020/NĐ-CP",
            content="Nội dung kiểm thử đầy đủ",
            source_page=3,
            hierarchy_level=2
        )

        assert doc.source_url == "https://vanban.chinhphu.vn/126-2020-nd-cp"
        assert chunk.article_number == "1a"
        assert chunk.source_page == 3
    else:
        models_path = Path(__file__).resolve().parents[1] / "registry" / "models.py"
        source_code = models_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code)

        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        assert "LegalDocument" in classes
        assert "LegalChunk" in classes
        assert "LegalDocumentAmendment" in classes

        for field in expected_doc_cols:
            assert field in source_code, f"Thiếu trường '{field}' trong LegalDocument"
        for field in expected_chunk_cols:
            assert field in source_code, f"Thiếu trường '{field}' trong LegalChunk"
        for field in expected_amendment_cols:
            assert field in source_code, f"Thiếu trường '{field}' trong LegalDocumentAmendment"

        # Cho phép định dạng xuống dòng: article_number = Column(\n String(...)
        assert re.search(r"article_number\s*=\s*Column\(\s*String", source_code) is not None