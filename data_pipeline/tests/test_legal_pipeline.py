import json
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


def test_chunker_status_not_yet_effective():
    """Trường hợp 1: Có effective_date nhưng chưa tới ngày có hiệu lực -> giữ CHUA_XAC_DINH."""
    text = """
Điều 3. Hiệu lực thi hành
Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2028.
"""
    meta = {
        "doc_type": "LUAT",
        "effective_date": datetime(2028, 1, 1),
        "as_of": datetime(2026, 11, 14),
    }
    chunks = chunk_legal_document(text, "99/2026/QH15", hierarchy_level=1, metadata=meta)

    assert len(chunks) == 1
    assert chunks[0]["status"] == "CHUA_XAC_DINH"


def test_chunker_status_expired():
    """Trường hợp 2: Có effective_date hợp lệ nhưng đã quá expiry_date -> HET_HIEU_LUC."""
    text = """
Điều 3. Hiệu lực thi hành
Thông tư này áp dụng cho kỳ tính thuế năm 2020.
"""
    meta = {
        "doc_type": "THONG_TU",
        "effective_date": datetime(2020, 1, 1),
        "expiry_date": datetime(2021, 12, 31),
        "as_of": datetime(2026, 11, 14),
    }
    chunks = chunk_legal_document(text, "10/2020/TT-BTC", hierarchy_level=3, metadata=meta)

    assert len(chunks) == 1
    assert chunks[0]["status"] == "HET_HIEU_LUC"


def test_chunker_status_expired_on_exact_expiry_date():
    """expiry_date là ngày bắt đầu hết hiệu lực: as_of == expiry_date (>=) -> HET_HIEU_LUC."""
    text = """
Điều 3. Hiệu lực thi hành
Văn bản hết hiệu lực kể từ ngày 01/01/2026.
"""
    meta = {
        "doc_type": "THONG_TU",
        "effective_date": datetime(2020, 1, 1),
        "expiry_date": datetime(2026, 1, 1),
        "as_of": datetime(2026, 1, 1),
    }
    chunks = chunk_legal_document(text, "10/2020/TT-BTC", hierarchy_level=3, metadata=meta)

    assert len(chunks) == 1
    assert chunks[0]["status"] == "HET_HIEU_LUC"


def test_chunker_status_invalid_date_strings():
    """Ngày sai định dạng như 'invalid' phải giữ CHUA_XAC_DINH, không tự suy ra CON_HIEU_LUC."""
    text = """
Điều 3. Hiệu lực thi hành
Nội dung kiểm thử định dạng ngày lỗi.
"""
    chunks_bad_exp = chunk_legal_document(
        text,
        "10/2020/TT-BTC",
        hierarchy_level=3,
        metadata={
            "effective_date": "2020-01-01",
            "expiry_date": "invalid",
            "as_of": "2026-11-14",
        },
    )
    assert chunks_bad_exp[0]["status"] == "CHUA_XAC_DINH"

    chunks_bad_eff = chunk_legal_document(
        text,
        "10/2020/TT-BTC",
        hierarchy_level=3,
        metadata={
            "effective_date": "invalid",
            "as_of": "2026-11-14",
        },
    )
    assert chunks_bad_eff[0]["status"] == "CHUA_XAC_DINH"


def test_chunker_enriched_metadata():
    """Kiểm tra bổ sung nguồn, trang, hiệu lực, phiên bản và trạng thái mặc định khi thiếu ngày hiệu lực."""
    text = """
Điều 2. Đối tượng áp dụng
Áp dụng đối với doanh nghiệp hoạt động tại Việt Nam.
"""
    chunks_no_date = chunk_legal_document(text, "99/2025/NĐ-CP", hierarchy_level=2, source_page=3)
    assert chunks_no_date[0]["status"] == "CHUA_XAC_DINH"

    chunks_active = chunk_legal_document(
        text,
        "99/2025/NĐ-CP",
        hierarchy_level=2,
        source_page=3,
        metadata={
            "effective_date": datetime(2025, 1, 1),
            "as_of": datetime(2026, 11, 14),
        },
    )
    assert chunks_active[0]["status"] == "CON_HIEU_LUC"

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
    """Kiểm tra các cột metadata mới (bao gồm tax_types, expiry_date) và kiểu chuỗi của clause_number."""
    doc_cols = set(LegalDocument.__table__.columns.keys())
    chunk_cols = set(LegalChunk.__table__.columns.keys())
    amend_cols = set(LegalDocumentAmendment.__table__.columns.keys())

    assert {
        "source_url",
        "total_pages",
        "tax_types",
        "effective_date",
        "expiry_date",
        "status",
        "version",
        "amends_doc_code",
        "replaces_doc_code",
    }.issubset(doc_cols)
    assert {
        "article_intro",
        "clause_intro",
        "source_page",
        "source_url",
        "tax_types",
        "effective_date",
        "expiry_date",
        "status",
        "version",
    }.issubset(chunk_cols)
    assert {"original_doc_id", "amending_doc_id", "amendment_type", "effective_date"}.issubset(amend_cols)
    assert LegalChunk.__table__.columns["clause_number"].type.python_type is str
    assert LegalDocument.__table__.columns["status"].default.arg == "CHUA_XAC_DINH"


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_sync_ocr_pages_metadata_and_upsert():
    """Kiểm tra đồng bộ siêu dữ liệu đa trang OCR, đoạn mở đầu, 3 trạng thái và Upsert vào DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.parser.chunker import chunk_ocr_pages
    from data_pipeline.registry.models import Base
    from data_pipeline.registry.repository import sync_parsed_document

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        ocr_pages = [
            {
                "page": 1,
                "text": (
                    "CHÍNH PHỦ\n"
                    "Căn cứ Luật Quản lý thuế ngày 13 tháng 6 năm 2019;\n"
                    "Điều 1a. Phạm vi điều chỉnh bổ sung\n"
                    "1. Quy định chi tiết thi hành một số điều."
                ),
            },
            {
                "page": 2,
                "text": (
                    "2a. Bổ sung đối tượng áp dụng mới.\n"
                    "Điều 16. Quyền của người nộp thuế\n"
                    "1. Được hướng dẫn giải thích về thuế."
                ),
            },
        ]

        meta_v1 = {
            "doc_code": "126/2020/NĐ-CP",
            "title": "Nghị định quy định chi tiết Luật Quản lý thuế",
            "doc_type": "NGHI_DINH",
            "hierarchy_level": 2,
            "effective_date": datetime(2020, 12, 5),
            "as_of": datetime(2026, 11, 18),
            "source_url": "https://vanban.chinhphu.vn/126-2020-nd-cp",
            "tax_types": ["VAT", "TNDN"],
            "version": "1.0",
            "ocr_quality_status": "VERIFIED",
            "expert_review_status": "PENDING",
        }

        chunks = chunk_ocr_pages(
            pages=ocr_pages,
            doc_code=meta_v1["doc_code"],
            hierarchy_level=2,
            metadata=meta_v1,
        )

        doc = sync_parsed_document(session, meta_v1, chunks)

        assert "Căn cứ Luật Quản lý thuế" in doc.preamble
        assert doc.source_url == "https://vanban.chinhphu.vn/126-2020-nd-cp"
        assert doc.tax_types == ["VAT", "TNDN"]
        assert doc.version == "1.0"
        assert doc.total_pages == 2
        assert doc.status == "CON_HIEU_LUC"
        assert doc.ocr_quality_status == "VERIFIED"
        assert doc.expert_review_status == "PENDING"

        saved_chunks = session.query(LegalChunk).filter_by(doc_id=doc.id).all()
        assert len(saved_chunks) == 3

        c_1a_1 = next(c for c in saved_chunks if c.article_number == "1a" and c.clause_number == "1")
        c_1a_2a = next(c for c in saved_chunks if c.article_number == "1a" and c.clause_number == "2a")
        c_16_1 = next(c for c in saved_chunks if c.article_number == "16" and c.clause_number == "1")

        assert c_1a_1.source_page == 1
        assert c_1a_2a.source_page == 2
        assert c_16_1.source_page == 2
        assert c_1a_1.tax_types == ["VAT", "TNDN"]

        meta_v2 = {**meta_v1, "version": "2.0", "expert_review_status": "APPROVED"}
        updated_doc = sync_parsed_document(session, meta_v2, chunks)

        assert session.query(LegalDocument).count() == 1
        assert updated_doc.version == "2.0"
        assert updated_doc.expert_review_status == "APPROVED"
        assert session.query(LegalChunk).count() == 3
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_ingest_ocr_document_end_to_end(tmp_path):
    """Kiểm tra luồng chuẩn hóa và nạp trọn gói qua ingest_ocr_document và ingest_from_json."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_from_json, ingest_ocr_document
    from data_pipeline.registry.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        ocr_pages = [
            {
                "page": 1,
                "text": (
                    "CHÍNH PHỦ\n"
                    "Căn cứ Luật Quản lý thuế ngày 13 tháng 6 năm 2019;\n"
                    "Điều 1a. Phạm vi điều chỉnh bổ sung\n"
                    "1. Quy định chi tiết thi hành một số điều."
                ),
            },
            {
                "page": 2,
                "text": (
                    "2a. Bổ sung đối tượng áp dụng mới.\n"
                    "Điều 16. Quyền của người nộp thuế\n"
                    "1. Được hướng dẫn giải thích về thuế."
                ),
            },
        ]

        meta_v1 = {
            "doc_code": " 126/2020/NĐ-CP ",
            "title": "Nghị định quy định chi tiết Luật Quản lý thuế",
            "doc_type": "Nghị định",
            "effective_date": datetime(2020, 12, 5),
            "as_of": datetime(2026, 11, 18),
            "source_url": "https://vanban.chinhphu.vn/126-2020-nd-cp",
            "tax_types": ["VAT", "TNCN"],
            "version": "1.0",
            "ocr_quality_status": "verified",
            "expert_review_status": "pending",
        }

        doc = ingest_ocr_document(session, ocr_pages, meta_v1)

        assert doc.doc_code == "126/2020/NĐ-CP"
        assert doc.doc_type == "NGHI_DINH"
        assert doc.hierarchy_level == 2
        assert doc.status == "CON_HIEU_LUC"
        assert doc.ocr_quality_status == "VERIFIED"
        assert doc.expert_review_status == "PENDING"
        assert doc.total_pages == 2
        assert doc.tax_types == ["VAT", "TNCN"]
        assert session.query(LegalChunk).filter_by(doc_id=doc.id).count() == 3

        
        meta_v2 = {**meta_v1, "version": "2.0", "expert_review_status": "approved"}
        updated_doc = ingest_ocr_document(session, ocr_pages, meta_v2)

        assert session.query(LegalDocument).count() == 1
        assert updated_doc.version == "2.0"
        assert updated_doc.expert_review_status == "APPROVED"
        assert session.query(LegalChunk).count() == 3

        
        json_file = tmp_path / "sample_doc.json"
        json_file.write_text(
            json.dumps(
                {
                    "metadata": {
                        "doc_code": "38/2019/QH14",
                        "title": "Luật Quản lý thuế",
                        "doc_type": "Luật",
                    },
                    "ocr_pages": [
                        {
                            "page": 1,
                            "text": "Điều 1. Phạm vi điều chỉnh\nLuật này quy định việc quản lý các loại thuế.",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        json_doc = ingest_from_json(session, json_file)
        assert json_doc.doc_code == "38/2019/QH14"
        assert json_doc.hierarchy_level == 1
        assert session.query(LegalDocument).count() == 2

        # Báo lỗi khi thiếu doc_code
        with pytest.raises(ValueError, match="doc_code"):
            ingest_ocr_document(session, ocr_pages, {"title": "Thiếu số hiệu"})
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_ingest_rejects_invalid_data_without_polluting_registry(tmp_path):
    """Chặn dữ liệu không hợp lệ và đảm bảo sổ đăng ký không bị ghi rác."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_from_json, ingest_ocr_document
    from data_pipeline.registry.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    valid_pages = [{"page": 1, "text": "Điều 1. Phạm vi\nQuy định chung."}]

    try:
        
        with pytest.raises(ValueError, match="doc_code"):
            ingest_ocr_document(session, valid_pages, {"doc_code": "   "})

        
        with pytest.raises(ValueError, match="expiry_date"):
            ingest_ocr_document(
                session,
                valid_pages,
                {
                    "doc_code": "10/2025/TT-BTC",
                    "effective_date": datetime(2025, 5, 1),
                    "expiry_date": datetime(2025, 1, 1),
                },
            )

        
        with pytest.raises(ValueError, match="ocr_pages"):
            ingest_ocr_document(session, [], {"doc_code": "10/2025/TT-BTC"})

        
        with pytest.raises(ValueError, match="điều khoản hợp lệ"):
            ingest_ocr_document(
                session,
                [{"page": 1, "text": "Chỉ có tiêu đề, không có điều khoản nào"}],
                {"doc_code": "10/2025/TT-BTC"},
            )

       
        bad_json = tmp_path / "bad.json"
        bad_json.write_text(
            json.dumps({"metadata": {"doc_code": "10/2025/TT-BTC"}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="metadata"):
            ingest_from_json(session, bad_json)

        
        assert session.query(LegalDocument).count() == 0
        assert session.query(LegalChunk).count() == 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_ingest_idempotency_and_chunk_replacement():
    """Chạy nạp lặp lại không tạo bản sao; cập nhật bản mới sẽ thay thế sạch danh sách chunk cũ."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_ocr_document
    from data_pipeline.registry.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    pages_v1 = [
        {"page": 1, "text": "Điều 1. Quy định A\n1. Nội dung 1.\n2. Nội dung 2."}
    ]
    pages_v2 = [
        {"page": 1, "text": "Điều 1. Quy định A sửa đổi\n1. Nội dung duy nhất sau sửa đổi."}
    ]
    meta = {"doc_code": "80/2021/TT-BTC", "doc_type": "Thông tư", "version": "1.0"}

    try:
        
        ingest_ocr_document(session, pages_v1, meta)
        ingest_ocr_document(session, pages_v1, meta)
        assert session.query(LegalDocument).count() == 1
        assert session.query(LegalChunk).count() == 2

        # Nạp phiên bản 2 chỉ còn 1 khoản -> chunk thừa của v1 phải được xóa sạch
        ingest_ocr_document(session, pages_v2, {**meta, "version": "2.0"})
        assert session.query(LegalDocument).count() == 1
        chunks = session.query(LegalChunk).all()
        assert len(chunks) == 1
        assert "sau sửa đổi" in chunks[0].content
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_ingest_persists_to_real_database_file(tmp_path):
    """Kiểm tra dữ liệu được ghi thật xuống file DB và đọc lại được ở phiên kết nối mới."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_ocr_document
    from data_pipeline.registry.models import Base

    db_file = tmp_path / "legal_registry.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    
    with SessionLocal() as write_session:
        ingest_ocr_document(
            write_session,
            [{"page": 3, "text": "Điều 5. Khai thuế\n1. Người nộp thuế khai chính xác."}],
            {
                "doc_code": "38/2019/QH14",
                "title": "Luật Quản lý thuế",
                "doc_type": "Luật",
                "source_url": "https://vanban.chinhphu.vn/38-2019-qh14",
                "tax_types": ["VAT", "TNDN"],
            },
        )

    # Phiên 2: Mở kết nối mới hoàn toàn để kiểm tra dữ liệu đã lưu bền vững
    with SessionLocal() as read_session:
        doc = read_session.query(LegalDocument).filter_by(doc_code="38/2019/QH14").first()
        assert doc is not None
        assert doc.hierarchy_level == 1
        assert doc.total_pages == 3
        assert doc.tax_types == ["VAT", "TNDN"]
        chunks = read_session.query(LegalChunk).filter_by(doc_id=doc.id).all()
        assert len(chunks) == 1
        assert chunks[0].source_page == 3
        assert chunks[0].source_url == "https://vanban.chinhphu.vn/38-2019-qh14"
        assert chunks[0].tax_types == ["VAT", "TNDN"]

    engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_audit_document_chunks_detects_all_segment_issues():
    """Kiểm tra phát hiện đầy đủ các lỗi: thiếu URL/tax_types, trùng ID, thiếu trang, nội dung ngắn và thiếu Điều."""
    from data_pipeline.registry.ingestor import audit_document_chunks

    doc = LegalDocument(
        doc_code="99/2025/NĐ-CP",
        title="Nghị định kiểm thử audit",
        ocr_quality_status="VERIFIED",
        effective_date=datetime(2025, 1, 1),
    )

    chunks = [
        LegalChunk(
            article_number="1",
            clause_number="1",
            point_letter="",
            citation_path="Khoản 1, Điều 1, 99/2025/NĐ-CP",
            content="Nội dung hợp lệ đầy đủ quy định về quản lý thuế.",
            source_page=1,
        ),
        LegalChunk(
            article_number="1",
            clause_number="1",
            point_letter="",
            citation_path="Khoản 1, Điều 1, 99/2025/NĐ-CP",
            content="Ngắn",
            source_page=None,
        ),
        LegalChunk(
            article_number="3",
            clause_number="1",
            point_letter="",
            citation_path="Khoản 1, Điều 3, 99/2025/NĐ-CP",
            content="Nội dung Điều 3 đầy đủ nhưng bị nhảy cóc thiếu Điều 2.",
            source_page=2,
        ),
    ]

    issues = audit_document_chunks(doc, chunks)
    issue_types = {item["issue_type"] for item in issues}

    assert "MISSING_OR_INVALID_SOURCE_URL" in issue_types
    assert "MISSING_TAX_TYPES" in issue_types
    assert "DUPLICATE_STABLE_ID" in issue_types
    assert "MISSING_SOURCE_PAGE" in issue_types
    assert "EMPTY_OR_SHORT_CONTENT" in issue_types
    assert "MISSING_ARTICLE_SEQUENCE" in issue_types
    missing_issue = next(i for i in issues if i["issue_type"] == "MISSING_ARTICLE_SEQUENCE")
    assert missing_issue["missing_articles"] == [2]


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_batch_ingest_versioned_snapshot_stable_id_and_issue_report(tmp_path):
    """Kiểm tra nạp theo đợt, xuất snapshot có phiên bản, giữ ID ổn định và báo cáo đoạn thiếu/lỗi."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_batch_with_snapshot
    from data_pipeline.registry.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    batch_dir = tmp_path / "batch_01"
    out_dir = tmp_path / "snapshots"
    batch_dir.mkdir()

    
    (batch_dir / "01_missing_article.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "doc_code": "126/2020/NĐ-CP",
                    "title": "Nghị định 126",
                    "doc_type": "Nghị định",
                    "effective_date": "2020-12-05",
                    "source_url": "https://vanban.chinhphu.vn/126",
                    "tax_types": ["VAT", "TNDN"],
                    "version": "1.0",
                    "ocr_quality_status": "VERIFIED",
                },
                "ocr_pages": [
                    {
                        "page": 1,
                        "text": (
                            "Điều 1. Phạm vi điều chỉnh\n"
                            "1. Quy định chi tiết thi hành Luật Quản lý thuế.\n"
                            "Điều 3. Đối tượng áp dụng\n"
                            "1. Cơ quan thuế và người nộp thuế."
                        ),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    
    (batch_dir / "02_unverified.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "doc_code": "80/2021/TT-BTC",
                    "title": "Thông tư 80",
                    "doc_type": "Thông tư",
                    "ocr_quality_status": "RAW",
                },
                "ocr_pages": [
                    {
                        "page": 1,
                        "text": "Điều 1. Phạm vi\n1. Hướng dẫn thi hành một số điều.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    
    (batch_dir / "03_broken.json").write_text(
        json.dumps(
            {
                "metadata": {"title": "File hỏng thiếu số hiệu"},
                "ocr_pages": [{"page": 1, "text": "Điều 1. Test\nNội dung."}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        
        with pytest.raises(FileNotFoundError):
            ingest_batch_with_snapshot(session, tmp_path / "khong_ton_tai", out_dir, "v1.0")

        
        snap_v1, issues_v1, summary_v1 = ingest_batch_with_snapshot(
            session, batch_dir, out_dir, snapshot_version="v1.0"
        )

        assert snap_v1.exists() and issues_v1.exists()
        assert summary_v1["total_files"] == 3
        assert summary_v1["ingested_documents"] == 2
        assert summary_v1["failed_documents"] == 1
        assert summary_v1["total_chunks"] == 3

        data_v1 = json.loads(snap_v1.read_text(encoding="utf-8"))
        issues_data = json.loads(issues_v1.read_text(encoding="utf-8"))

        ids_v1 = [c["stable_id"] for d in data_v1["documents"] for c in d["chunks"]]
        assert "126/2020/NĐ-CP::D1::K1::P0" in ids_v1
        assert "126/2020/NĐ-CP::D3::K1::P0" in ids_v1

       
        doc_126 = next(d for d in data_v1["documents"] if d["doc_code"] == "126/2020/NĐ-CP")
        assert doc_126["source_url"] == "https://vanban.chinhphu.vn/126"
        assert doc_126["tax_types"] == ["VAT", "TNDN"]
        assert doc_126["version"] == "1.0"
        assert doc_126["effective_date"].startswith("2020-12-05")
        assert doc_126["chunks"][0]["source_page"] == 1
        assert doc_126["chunks"][0]["tax_types"] == ["VAT", "TNDN"]

       
        assert len(issues_data["failed_documents"]) == 1
        assert issues_data["failed_documents"][0]["source_file"] == "03_broken.json"

        issue_types = {item["issue_type"] for item in issues_data["segment_issues"]}
        assert "MISSING_ARTICLE_SEQUENCE" in issue_types
        assert "UNVERIFIED_OCR" in issue_types
        assert "MISSING_EFFECTIVE_DATE" in issue_types
        assert "MISSING_OR_INVALID_SOURCE_URL" in issue_types
        assert "MISSING_TAX_TYPES" in issue_types

      
        snap_v2, _, _ = ingest_batch_with_snapshot(
            session, batch_dir, out_dir, snapshot_version="v1.1"
        )
        data_v2 = json.loads(snap_v2.read_text(encoding="utf-8"))
        ids_v2 = [c["stable_id"] for d in data_v2["documents"] for c in d["chunks"]]

        assert ids_v1 == ids_v2
        assert session.query(LegalDocument).count() == 2
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not HAS_SQLALCHEMY, reason="SQLAlchemy chưa tải được trên môi trường này")
def test_backend_required_fields_and_strict_mode(tmp_path):
    """Kiểm tra đủ effective_date, expiry_date, source_page, source_url (https), tax_types trên từng đoạn luật."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data_pipeline.registry.ingestor import ingest_batch_with_snapshot, ingest_ocr_document
    from data_pipeline.registry.models import Base
    from data_pipeline.registry.repository import normalize_tax_types

    
    assert normalize_tax_types("vat, TNDN, vat , tncn") == ["VAT", "TNDN", "TNCN"]
    assert normalize_tax_types(["VAT", "tndn", "VAT"]) == ["VAT", "TNDN"]
    with pytest.raises(ValueError, match="tax_types"):
        normalize_tax_types(12345)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    valid_pages = [
        {"page": 4, "text": "Điều 1. Đối tượng chịu thuế\n1. Hàng hóa, dịch vụ dùng cho sản xuất kinh doanh."}
    ]

    try:
        # Chặn link không phải https://
        with pytest.raises(ValueError, match="https://"):
            ingest_ocr_document(
                session,
                valid_pages,
                {"doc_code": "48/2024/QH15", "source_url": "http://vanban.chinhphu.vn/48"},
            )

        
        with pytest.raises(ValueError, match="effective_date"):
            ingest_ocr_document(
                session,
                valid_pages,
                {
                    "doc_code": "48/2024/QH15",
                    "source_url": "https://vanban.chinhphu.vn/48",
                    "tax_types": ["VAT"],
                },
                strict=True,
            )

        with pytest.raises(ValueError, match="source_url"):
            ingest_ocr_document(
                session,
                valid_pages,
                {
                    "doc_code": "48/2024/QH15",
                    "effective_date": "2025-07-01",
                    "tax_types": ["VAT"],
                },
                strict=True,
            )

        with pytest.raises(ValueError, match="tax_types"):
            ingest_ocr_document(
                session,
                valid_pages,
                {
                    "doc_code": "48/2024/QH15",
                    "effective_date": "2025-07-01",
                    "source_url": "https://vanban.chinhphu.vn/48",
                },
                strict=True,
            )

        with pytest.raises(ValueError, match="source_page"):
            ingest_ocr_document(
                session,
                [{"page": None, "text": "Điều 1. Test\n1. Thiếu số trang PDF."}],
                {
                    "doc_code": "48/2024/QH15",
                    "effective_date": "2025-07-01",
                    "source_url": "https://vanban.chinhphu.vn/48",
                    "tax_types": ["VAT"],
                },
                strict=True,
            )

       
        batch_dir = tmp_path / "strict_batch"
        out_dir = tmp_path / "strict_out"
        batch_dir.mkdir()
        (batch_dir / "luat_vat.json").write_text(
            json.dumps(
                {
                    "metadata": {
                        "doc_code": "48/2024/QH15",
                        "title": "Luật Thuế giá trị gia tăng",
                        "doc_type": "Luật",
                        "effective_date": "2025-07-01",
                        "expiry_date": "2030-01-01",
                        "source_url": "https://vanban.chinhphu.vn/48-2024-qh15",
                        "tax_types": ["vat", "TNDN"],
                        "ocr_quality_status": "VERIFIED",
                    },
                    "ocr_pages": valid_pages,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        snap_file, issues_file, summary = ingest_batch_with_snapshot(
            session, batch_dir, out_dir, snapshot_version="v2.0", strict=True
        )
        assert summary["ingested_documents"] == 1
        assert summary["failed_documents"] == 0
        assert summary["total_segment_issues"] == 0

        saved_chunk = session.query(LegalChunk).one()
        assert saved_chunk.effective_date == datetime(2025, 7, 1)
        assert saved_chunk.expiry_date == datetime(2030, 1, 1)
        assert saved_chunk.source_page == 4
        assert saved_chunk.source_url == "https://vanban.chinhphu.vn/48-2024-qh15"
        assert saved_chunk.tax_types == ["VAT", "TNDN"]

        snap_data = json.loads(snap_file.read_text(encoding="utf-8"))
        chunk_json = snap_data["documents"][0]["chunks"][0]
        assert chunk_json["effective_date"].startswith("2025-07-01")
        assert chunk_json["expiry_date"].startswith("2030-01-01")
        assert chunk_json["source_page"] == 4
        assert chunk_json["source_url"] == "https://vanban.chinhphu.vn/48-2024-qh15"
        assert chunk_json["tax_types"] == ["VAT", "TNDN"]
        assert json.loads(issues_file.read_text(encoding="utf-8"))["segment_issues"] == []
    finally:
        session.close()
        engine.dispose()