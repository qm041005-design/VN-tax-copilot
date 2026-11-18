"""
tests/test_migrations.py  –  NÂNG CẤP DB CŨ BẰNG backend/migrations/*.sql (chỉ PostgreSQL)
=========================================================================================
Mô phỏng một DB đang chạy với schema bảng luật CŨ (clause_number kiểu số, chưa có các cột của nhóm 5)
và đã có dữ liệu, rồi chạy 001 + 002 (hai lần). Kiểm tra: không mất dữ liệu, schema khớp model hiện tại,
API vẫn đọc được. Chạy với TEST_DATABASE_URL trỏ vào PostgreSQL (CI có sẵn); SQLite -> bỏ qua.
"""
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.core.database import Base, SessionLocal, engine
from app.models import LegalChunk, LegalDocument
from app.services import source_service
from tests.conftest import _drop_every_table

if engine.dialect.name != "postgresql":
    pytest.skip("Migration SQL chỉ dành cho PostgreSQL", allow_module_level=True)

MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql"))

# Schema bảng luật trước khi đồng bộ với nhóm 5 (backend cũ, trước 001)
OLD_SCHEMA = """
CREATE TABLE legal_documents (
    id serial PRIMARY KEY, doc_code varchar(100) NOT NULL UNIQUE, title varchar(500) NOT NULL,
    doc_type varchar(50) NOT NULL, hierarchy_level integer NOT NULL, issuer varchar(200),
    source_url varchar(1000), issue_date timestamp, effective_date timestamp, expiry_date timestamp,
    version varchar(50) NOT NULL, amends_doc_code varchar(100), created_at timestamp, updated_at timestamp);
CREATE TABLE legal_chunks (
    id serial PRIMARY KEY, doc_id integer NOT NULL REFERENCES legal_documents(id),
    article_number varchar(20) NOT NULL, article_title varchar(300), clause_number integer,
    point_letter varchar(5), citation_path varchar(500) NOT NULL, content text NOT NULL,
    source_page integer, hierarchy_level integer NOT NULL);
INSERT INTO legal_documents (doc_code, title, doc_type, hierarchy_level, version)
    VALUES ('CU-01', 'Văn bản nạp từ trước', 'LUAT', 1, '1.0');
INSERT INTO legal_chunks (doc_id, article_number, clause_number, point_letter, citation_path, content, hierarchy_level)
    SELECT id, '9', 3, 'a', 'Điểm a, Khoản 3, Điều 9, CU-01', 'Thuế suất phổ thông dữ liệu cũ.', 1 FROM legal_documents;
INSERT INTO legal_chunks (doc_id, article_number, clause_number, citation_path, content, hierarchy_level)
    SELECT id, '10', NULL, 'Điều 10, CU-01', 'Điều không có Khoản, dữ liệu cũ.', 1 FROM legal_documents;
"""


def _run_sql(sql: str):
    conn = engine.raw_connection()
    try:
        conn.cursor().execute(sql)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def old_db():
    _drop_every_table()
    _run_sql(OLD_SCHEMA)
    yield
    _drop_every_table()


def test_migration_nang_cap_db_cu_khong_mat_du_lieu(old_db):
    assert [m.name for m in MIGRATIONS][:2] == ["001_clause_number_text.sql", "002_legal_status_and_registry_columns.sql"]
    for _ in range(2):  # chạy lại lần 2 không được lỗi
        for m in MIGRATIONS:
            _run_sql(m.read_text(encoding="utf-8"))

    # Schema sau migration khớp model hiện tại: đủ cột, đúng kiểu, đúng NULL
    insp = inspect(engine)
    for table in ("legal_documents", "legal_chunks", "legal_document_tax_scopes"):
        db_cols = {c["name"]: c for c in insp.get_columns(table)}
        for col in Base.metadata.tables[table].columns:
            assert col.name in db_cols, f"{table}.{col.name} chưa được migration thêm vào"
            got = db_cols[col.name]
            db_type, model_type = got["type"].compile(engine.dialect), col.type.compile(engine.dialect)
            assert db_type == model_type, f"{table}.{col.name}: DB {db_type} khác model {model_type}"
            assert got["nullable"] == col.nullable, f"{table}.{col.name} sai NULL/NOT NULL"

    # Dữ liệu cũ còn nguyên, cột mới nhận giá trị mặc định
    with SessionLocal() as db:
        chunks = {c.article_number: c for c in db.query(LegalChunk).all()}
        assert chunks["9"].clause_number == "3" and chunks["9"].point_letter == "a"
        assert chunks["10"].clause_number == "0"            # NULL cũ -> "0" (không có Khoản)
        assert {c.status for c in chunks.values()} == {"CHUA_XAC_DINH"}
        assert {c.version for c in chunks.values()} == {"1.0"}
        assert db.query(LegalDocument).one().status == "CHUA_XAC_DINH"

        # Ghi mới bằng model hiện tại (có cột của nhóm 5) và tìm kiếm vẫn chạy
        doc = LegalDocument(doc_code="MOI-01", title="Văn bản mới", doc_type="NGHI_DINH", hierarchy_level=2,
                            status="CON_HIEU_LUC", total_pages=3)
        db.add(doc)
        db.flush()
        db.add(LegalChunk(doc_id=doc.id, article_number="1a", clause_number="2a", point_letter="b",
                          citation_path="Điểm b, Khoản 2a, Điều 1a, MOI-01", hierarchy_level=2,
                          article_intro="Mở đầu", content="Thuế suất phổ thông dữ liệu mới."))
        db.commit()
        found = {source_service.to_hit(c).citation_path: source_service.to_hit(c)
                 for c, _ in source_service.search(db, "thuế suất phổ thông")}
    assert found["Điểm a, Khoản 3, Điều 9, CU-01"].khoan == "3"
    assert found["Điểm b, Khoản 2a, Điều 1a, MOI-01"].khoan == "2a"
