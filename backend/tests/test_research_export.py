"""
tests/test_research_export.py  –  LƯU KẾT QUẢ 6 PHẦN VÀO LỊCH SỬ + XUẤT WORD (SCRUM-33)
=====================================================================================
1. POST /research lưu research_result; GET /matters/{id}/history trả lại khi mở hồ sơ.
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
