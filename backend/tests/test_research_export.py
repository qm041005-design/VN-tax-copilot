"""
tests/test_research_export.py  –  LƯU KẾT QUẢ 6 PHẦN VÀO LỊCH SỬ + XUẤT WORD (SCRUM-33)
=====================================================================================
1. POST /research lưu research_result; GET /matters/{id}/history trả lại khi mở hồ sơ.
2. GET /matters/{id}/history/{hid}/export: kiểm tra quyền TRƯỚC khi xuất, dùng module Word của Quân.
"""
import io
from datetime import datetime

import pytest
from docx import Document

from app.core.database import SessionLocal
from app.models import AuditLog, LegalChunk, LegalDocument
from tests.helpers import auth

A, B = auth("alice", "thtax"), auth("bob", "other")
SECTIONS = {"issue", "facts", "authority", "analysis", "limitations", "next_steps"}


@pytest.fixture()
def researched(client):
    """1 hồ sơ của alice + 1 lượt tra cứu có nguồn (đoạn luật có URL – module Word bắt buộc)."""
    with SessionLocal() as db:
        doc = LegalDocument(doc_code="48/2024/QH15", title="Luật Thuế GTGT", doc_type="LUAT", hierarchy_level=1,
                            effective_date=datetime(2025, 7, 1), source_url="https://vbpl.vn/48-2024-qh15")
        db.add(doc)
        db.flush()
        db.add(LegalChunk(doc_id=doc.id, article_number="9", clause_number="3", point_letter="a", hierarchy_level=1,
                          citation_path="Điểm a, Khoản 3, Điều 9, 48/2024/QH15",
                          content="Điểm a, Khoản 3, Điều 9: thuế suất 10% là mức phổ thông."))
        db.commit()
    mid = client.post("/api/v1/matters", json={"title": "Hồ sơ VAT", "client_name": "ABC", "tax_period": "2026"},
                      headers=A).json()["id"]
    r = client.post("/api/v1/research", json={"matter_id": mid, "question": "thuế suất phổ thông"}, headers=A)
    assert r.status_code == 201, r.text
    return mid, r.json()


def test_ket_qua_6_phan_duoc_luu_va_tra_lai_khi_mo_ho_so(client, researched):
    mid, body = researched
    saved = body["history"]["research_result"]
    assert saved == body["research_result"]                       # response và bản lưu là một
    assert set(saved["sections"]) == SECTIONS and saved["status"] in {"draft", "clarify", "abstain"}
    # Mở lại hồ sơ: lịch sử trả đúng object đã lưu
    history = client.get(f"/api/v1/matters/{mid}/history", headers=A).json()
    assert history[0]["id"] == body["history"]["id"] and history[0]["research_result"] == saved


def test_luot_tra_cuu_cu_khong_co_ket_qua_6_phan(client):
    mid = client.post("/api/v1/matters", json={"title": "t", "client_name": "c"}, headers=A).json()["id"]
    h = client.post(f"/api/v1/matters/{mid}/history", json={"question": "lưu tay"}, headers=A).json()
    assert h["research_result"] is None
    r = client.get(f"/api/v1/matters/{mid}/history/{h['id']}/export", headers=A)
    assert r.status_code == 409                                   # không tự dựng lại kết quả


def test_xuat_word(client, researched):
    mid, body = researched
    hid = body["history"]["id"]
    r = client.get(f"/api/v1/matters/{mid}/history/{hid}/export", headers=A)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")
    assert "attachment" in r.headers["content-disposition"]
    text = "\n".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert "Vấn đề pháp lý" in text                               # tiêu đề 1 trong 6 phần
    with SessionLocal() as db:                                    # có ghi audit
        assert db.query(AuditLog).filter_by(action="history.export_docx", resource_id=hid).count() == 1


def test_xuat_word_kiem_tra_quyen_truoc(client, researched):
    mid, body = researched
    hid = body["history"]["id"]
    url = f"/api/v1/matters/{mid}/history/{hid}/export"
    assert client.get(url).status_code == 401                     # chưa đăng nhập
    assert client.get(url, headers=B).status_code == 404          # tổ chức khác
    other = client.post("/api/v1/matters", json={"title": "khác", "client_name": "c"}, headers=A).json()["id"]
    assert client.get(f"/api/v1/matters/{other}/history/{hid}/export", headers=A).status_code == 404  # sai hồ sơ
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="history.export_docx").count() == 0


def test_xuat_word_khi_nguon_bi_xoa(client, researched):
    mid, body = researched
    with SessionLocal() as db:                                    # nguồn đã trích dẫn bị xóa khỏi kho
        db.query(LegalChunk).delete()
        db.commit()
    r = client.get(f"/api/v1/matters/{mid}/history/{body['history']['id']}/export", headers=A)
    assert r.status_code == 409 and "không còn trong kho" in r.json()["detail"]


def test_xuat_word_khi_nguon_khong_co_link(client, researched):
    mid, body = researched
    with SessionLocal() as db:                                    # module Word bắt buộc link http(s)
        db.query(LegalDocument).update({"source_url": None})
        db.commit()
    r = client.get(f"/api/v1/matters/{mid}/history/{body['history']['id']}/export", headers=A)
    assert r.status_code == 422 and r.json()["detail"].startswith("Không xuất được báo cáo")


def test_ho_so_da_luu_tru_van_xuat_duoc_nhung_khong_tra_cuu_them(client, researched):
    """Hồ sơ lưu trữ chỉ đọc: xem và xuất Word được (lưu hồ sơ kiểm toán), tra cứu thêm thì 409."""
    mid, body = researched
    assert client.delete(f"/api/v1/matters/{mid}", headers=A).status_code == 200
    r = client.get(f"/api/v1/matters/{mid}/history/{body['history']['id']}/export", headers=A)
    assert r.status_code == 200
    assert client.post("/api/v1/research", json={"matter_id": mid, "question": "thuế suất"}, headers=A).status_code == 409
