"""
tests/test_data_pipeline_sync.py  –  KIỂM TRA KHỚP GIỮA NHÓM 5 (data_pipeline, SCRUM-21) VÀ BACKEND
==================================================================================================
Dùng CODE THẬT của nhóm 5:
    parser  data_pipeline/parser/chunker.py   -> tách văn bản mẫu (giống test_run.py) thành đoạn trích
    ORM     data_pipeline/registry/models.py  -> ghi văn bản + đoạn trích vào DB
rồi gọi API backend /api/v1/sources để đọc ra, kiểm tra 3 điểm đã thống nhất:
    1. clause_number dạng chuỗi ("2a" giữ nguyên; "0" -> khoan = null)
    2. cột status ở legal_documents và legal_chunks
    3. hierarchy_level cấp 5 cho văn bản UNKNOWN

2 kịch bản: (a) bảng do models.py của nhóm 5 tạo; (b) bảng do backend tạo (create_all lúc khởi động).

Tìm data_pipeline ở: thư mục gốc repo (khi đã merge cùng nhánh) hoặc biến DATA_PIPELINE_ROOT
(đường dẫn tới thư mục repo có nhánh 05). Không tìm thấy -> test được BỎ QUA (skip), không báo lỗi.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

from app.core.database import Base, SessionLocal, engine
from tests.helpers import auth

_ROOT = os.environ.get("DATA_PIPELINE_ROOT") or str(Path(__file__).resolve().parents[2])
if not (Path(_ROOT) / "data_pipeline" / "parser" / "chunker.py").is_file():
    pytest.skip("Không có data_pipeline của nhóm 5 (đặt DATA_PIPELINE_ROOT để chạy)", allow_module_level=True)
sys.path.insert(0, _ROOT)

from data_pipeline.parser.chunker import chunk_legal_document  # noqa: E402
from data_pipeline.registry import models as dp  # noqa: E402
from data_pipeline.registry.hierarchy import get_hierarchy_level  # noqa: E402

A = auth("alice", "thtax")

# Văn bản mẫu y hệt test_run.py của nhóm 5
SAMPLE = """
Điều 1a. Phạm vi điều chỉnh bổ sung
Nghị định này quy định chi tiết thi hành một số điều của Luật Quản lý thuế bao gồm:
a) Khai thuế, tính thuế, ấn định thuế;
b) Hoàn thuế, miễn thuế, giảm thuế.

Điều 16. Quyền của người nộp thuế
1. Được hướng dẫn giải thích khi có yêu cầu.
2. Được nhận văn bản liên quan đến việc kiểm tra thuế bao gồm:
a) Quyết định kiểm tra thuế;
b) Biên bản kiểm tra thuế.
2a. Được bổ sung tài liệu giải trình trong thời hạn quy định.
"""
ND_CODE = "Nghị định số 126/2020/NĐ-CP"
UNK_CODE = "Văn bản chưa phân loại 01"

# Khóa trong dict của parser là thông tin CẤP VĂN BẢN, bảng legal_chunks không có -> đưa sang LegalDocument
DOC_LEVEL_KEYS = {"doc_type", "expiry_date", "amends_doc_code", "replaces_doc_code"}
CHUNK_COLUMNS = {c.name for c in dp.LegalChunk.__table__.columns}


def _load(doc_code: str, doc_type: str | None, meta: dict) -> None:
    """Nạp 1 văn bản: parser nhóm 5 -> ORM nhóm 5 (giống cách loader của nhóm 5 sẽ làm)."""
    level = get_hierarchy_level(doc_type)
    chunks = chunk_legal_document(SAMPLE, doc_code, hierarchy_level=level, source_page=3, metadata=meta)
    first = chunks[0]
    with SessionLocal() as db:
        doc = dp.LegalDocument(doc_code=doc_code, title=doc_code, doc_type=first["doc_type"], hierarchy_level=level,
                               effective_date=first["effective_date"], expiry_date=first["expiry_date"],
                               status=first["status"], version=first["version"])
        db.add(doc)
        db.flush()
        assert not (set(first) - CHUNK_COLUMNS - DOC_LEVEL_KEYS), "parser sinh khóa lạ, cần báo nhóm 5"
        db.add_all(dp.LegalChunk(doc_id=doc.id, **{k: v for k, v in c.items() if k in CHUNK_COLUMNS}) for c in chunks)
        db.commit()


@pytest.fixture(params=["bang_do_nhom5_tao", "bang_do_backend_tao"])
def loaded(request, client):
    # Bảng chỉ backend có (vd nhãn sắc thuế) mà có khóa ngoại tới legal_documents -> phải xóa trước bảng văn bản
    backend_only = [t for n, t in Base.metadata.tables.items() if n not in dp.Base.metadata.tables
                    and any(fk.column.table.name == "legal_documents" for fk in t.foreign_keys)]
    if request.param == "bang_do_nhom5_tao":
        # Bỏ bảng luật backend vừa tạo, để models.py của nhóm 5 tự tạo
        Base.metadata.drop_all(engine, tables=backend_only + [Base.metadata.tables["legal_chunks"],
                                                              Base.metadata.tables["legal_documents"]])
    dp.Base.metadata.create_all(engine)  # bảng đã có thì giữ nguyên, chỉ tạo thêm legal_document_amendments
    try:
        # chunk_legal_document không nhận tham số doc_type: phải truyền qua metadata, nếu không đoạn trích sẽ
        # mang doc_type "UNKNOWN" dù hierarchy_level = 2 (như test_run.py hiện tại) -> đã báo nhóm 5
        _load(ND_CODE, "NGHI_DINH", {"doc_type": "NGHI_DINH", "effective_date": datetime(2020, 12, 5),
                                     "as_of": datetime(2026, 11, 14)})
        _load(UNK_CODE, None, {})
        yield
    finally:
        Base.metadata.drop_all(engine, tables=backend_only)
        dp.Base.metadata.drop_all(engine)  # dọn cả bảng amendments (có khóa ngoại tới legal_documents)


def _cot(col) -> tuple:
    """Đặc điểm 1 cột: kiểu + độ dài, cho phép NULL, giá trị mặc định (hàm như utcnow chỉ so 'có/không')."""
    d = col.default.arg if col.default is not None else None
    return str(col.type), col.nullable, ("<ham>" if callable(d) else d), col.onupdate is not None


@pytest.mark.parametrize("bang", ["legal_documents", "legal_chunks"])
def test_schema_khop_tung_cot_voi_nhom5(bang):
    """So từng cột giữa data_pipeline/registry/models.py (nhóm 5) và app/models/legal_source.py (backend)."""
    a, b = dp.Base.metadata.tables[bang].columns, Base.metadata.tables[bang].columns
    assert set(a.keys()) == set(b.keys()), f"thiếu ở backend: {set(a.keys()) - set(b.keys())}, " \
                                           f"thừa ở backend: {set(b.keys()) - set(a.keys())}"
    lech = {n: (_cot(a[n]), _cot(b[n])) for n in a.keys() if _cot(a[n]) != _cot(b[n])}
    assert not lech, f"cột lệch (nhóm 5, backend): {lech}"


def test_3_yeu_cau_cua_nhom5():
    """Đúng 3 điểm trong tin nhắn của thành viên 5 (SCRUM-21)."""
    chunks, docs = Base.metadata.tables["legal_chunks"].c, Base.metadata.tables["legal_documents"].c
    # 1. clause_number: String(20), mặc định "0"
    assert _cot(chunks.clause_number)[:3] == ("VARCHAR(20)", False, "0")
    # 2. status: String(50), mặc định CHUA_XAC_DINH, ở CẢ 2 bảng
    assert _cot(chunks.status)[:3] == _cot(docs.status)[:3] == ("VARCHAR(50)", False, "CHUA_XAC_DINH")
    # 3. hierarchy_level nhận cấp 5 cho UNKNOWN
    assert get_hierarchy_level("UNKNOWN") == 5 and docs.hierarchy_level.default.arg == 5


def _search(client, q: str) -> list[dict]:
    r = client.get("/api/v1/sources/search", params={"q": q, "limit": 50}, headers=A)
    assert r.status_code == 200, r.text
    return r.json()


def test_parser_nhom5_den_api_backend(client, loaded):
    hits = _search(client, "giải trình")
    # Tìm kiếm chấm điểm theo từng từ: "giải" còn khớp "hướng dẫn giải thích", nhưng Khoản 2a khớp đủ 2 từ -> đứng đầu
    nd = [h for h in hits if h["legal_identifier"] == ND_CODE]
    # 1. Khoản có hậu tố chữ giữ nguyên dạng chuỗi
    assert (nd[0]["dieu"], nd[0]["khoan"], nd[0]["diem"]) == ("16", "2a", None)
    assert nd[0]["citation_path"] == f"Khoản 2a, Điều 16, {ND_CODE}"
    # 2. status do parser tính từ ngày hiệu lực
    assert nd[0]["status"] == "CON_HIEU_LUC"
    assert nd[0]["doc_type"] == "NGHI_DINH" and nd[0]["hierarchy_level"] == 2

    # Điều 1a không có Khoản (clause_number "0") -> khoan = null, Điều giữ chữ "1a"
    dieu_1a = [h for h in _search(client, "ấn định thuế") if h["legal_identifier"] == ND_CODE]
    assert (dieu_1a[0]["dieu"], dieu_1a[0]["khoan"], dieu_1a[0]["diem"]) == ("1a", None, "a")

    # 3. Văn bản UNKNOWN -> cấp 5, status CHUA_XAC_DINH (không kiểm thứ hạng: do thuật toán tìm kiếm quyết định)
    unk = [h for h in hits if h["legal_identifier"] == UNK_CODE]
    assert unk[0]["doc_type"] == "UNKNOWN" and unk[0]["hierarchy_level"] == 5
    assert unk[0]["status"] == "CHUA_XAC_DINH"

    # Xem nguyên văn: có đủ câu mở đầu Khoản + trang nguồn
    detail = client.get(f"/api/v1/sources/{dieu_1a[0]['source_id']}", headers=A).json()
    assert "Nghị định này quy định chi tiết" in detail["content"] and detail["source_page"] == 3


def test_research_luu_trich_dan_khoan_chu(client, loaded):
    mid = client.post("/api/v1/matters", json={"title": "Quyền NNT", "client_name": "ABC"}, headers=A).json()["id"]
    r = client.post("/api/v1/research", json={"matter_id": mid, "question": "bổ sung tài liệu giải trình",
                                              "research_as_of": "2026-11-14"}, headers=A)
    assert r.status_code == 201, r.text
    top = r.json()["history"]["citations"][0]
    assert (top["legal_identifier"], top["dieu"], top["khoan"]) == (ND_CODE, "16", "2a")
