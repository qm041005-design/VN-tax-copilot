"""
tests/test_ai_integration.py  –  TÍCH HỢP ĐẦU-CUỐI: registry -> BM25 -> guardrails -> prompt tuần 4 -> lịch sử -> Word (SCRUM-36)
=====================================================================================================================
Model giả (không gọi AI thật): kiểm tra dây nối, không kiểm tra chất lượng câu trả lời hay tính đúng pháp lý.
"""
import io
import json
from datetime import datetime

import pytest
from docx import Document

from ai_engine.guardrails import EvidenceAssessment
from ai_engine.synthesis.backend_adapter import make_guarded_generator
from app.api.v1.research import _load, research_callbacks
from app.core.database import SessionLocal
from app.main import app
from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from tests.helpers import auth

A = auth("alice", "thtax")
ANSWER = "Hàng hóa không thuộc diện 0% và 5% áp dụng thuế suất 10% (câu trả lời giả lập)."
CALLS = []


def assess_all(safe):
    """Bộ đánh giá giả: chấp nhận mọi nguồn được gửi vào."""
    return [EvidenceAssessment(p["passage_id"], True, "sufficient") for p in safe.passages]


def fake_complete(messages):
    """Model giả: trả JSON 6 phần, trích dẫn nguồn đầu tiên mà prompt gửi tới."""
    CALLS.append(messages)
    pid = json.loads(messages[1]["content"])["passages"][0]["passage_id"]
    sections = {k: [] for k in ("issue", "facts", "authority", "analysis", "limitations", "next_steps")}
    sections["authority"] = [{"text": "Khoản 3 Điều 9 Luật Thuế GTGT.", "citation_ids": [pid]}]
    sections["analysis"] = [{"text": ANSWER, "citation_ids": [pid]}]
    return {"status": "draft", "sections": sections, "clarification_questions": [], "warnings": []}


@pytest.fixture()
def ai_wired(client):
    with SessionLocal() as db:
        doc = LegalDocument(doc_code="48/2024/QH15", title="Luật Thuế GTGT", doc_type="LUAT", hierarchy_level=1,
                            effective_date=datetime(2025, 7, 1), source_url="https://vbpl.vn/48-2024-qh15")
        db.add(doc)
        db.flush()
        db.add(LegalDocumentTaxScope(doc_id=doc.id, tax_type="VAT"))
        # source_page bắt buộc: module Word chỉ xuất trích dẫn có số trang PDF đã đối chiếu
        db.add(LegalChunk(doc_id=doc.id, article_number="9", clause_number="3", hierarchy_level=1, source_page=7,
                          citation_path="Khoản 3, Điều 9, 48/2024/QH15",
                          content="Khoản 3: Mức thuế suất 10% áp dụng đối với hàng hóa, dịch vụ không thuộc diện 0% và 5%."))
        db.commit()
    CALLS.clear()
    app.dependency_overrides[research_callbacks] = lambda: (assess_all, make_guarded_generator(fake_complete))
    yield client
    app.dependency_overrides.pop(research_callbacks, None)


def test_tra_cuu_ra_ban_nhap_6_phan_luu_lich_su_va_xuat_word(ai_wired):
    client = ai_wired
    mid = client.post("/api/v1/matters", json={"title": "VAT", "client_name": "ABC", "tax_types": ["VAT"],
                                               "tax_period": "2026"}, headers=A).json()["id"]
    r = client.post("/api/v1/research", headers=A, json={
        "matter_id": mid, "question": "Mức thuế suất 10% áp dụng cho hàng hóa nào?", "tax_type": "VAT",
        "material_facts": "Công ty bán máy tính cho doanh nghiệp trong nước",
        # câu hỏi thuế suất hàng hóa: guardrails (SCRUM-32) bắt buộc 3 dữ kiện có cấu trúc, thiếu là clarify
        "case_facts": {"goods_description": "Máy tính xách tay", "transaction_type": "Bán trong nước",
                       "transaction_date": "2026-03"}})
    assert r.status_code == 201, r.text
    body = r.json()
    result = body["research_result"]
    assert result["status"] == "draft" and result["sections"]["analysis"][0]["text"] == ANSWER
    assert body["history"]["answer"] and len(CALLS) == 1                    # model chỉ được gọi 1 lần, qua guardrails
    assert [c["legal_identifier"] for c in body["history"]["citations"]] == ["48/2024/QH15"]

    history = client.get(f"/api/v1/matters/{mid}/history", headers=A).json()   # mở lại hồ sơ
    assert history[0]["research_result"] == result

    word = client.get(f"/api/v1/matters/{mid}/history/{body['history']['id']}/export", headers=A)
    assert word.status_code == 200, word.text
    text = "\n".join(p.text for p in Document(io.BytesIO(word.content)).paragraphs)
    text += "\n".join(c.text for t in Document(io.BytesIO(word.content)).tables for row in t.rows for c in row.cells)
    assert ANSWER in text                                                     # nội dung AI đi tới file Word


def test_thieu_tinh_tiet_thi_khong_goi_model(ai_wired):
    client = ai_wired
    mid = client.post("/api/v1/matters", json={"title": "VAT", "client_name": "ABC", "tax_period": "2026"},
                      headers=A).json()["id"]
    r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "thuế suất 10%"})
    assert r.json()["research_result"]["status"] == "clarify" and CALLS == []


def test_doc_cau_hinh_module_ham():
    assert _load("") is None                                                 # không cấu hình = không bật AI
    assert _load("json:dumps") is json.dumps
    with pytest.raises(ModuleNotFoundError):
        _load("khong_ton_tai:ham")


def test_ca_3_trang_thai_deu_luu_va_mo_lai_dung(ai_wired):
    """SCRUM-36 task 3: draft / clarify / abstain đều lưu nguyên object 6 phần và trả lại khi mở hồ sơ."""
    client = ai_wired
    mid = client.post("/api/v1/matters", json={"title": "VAT", "client_name": "ABC", "tax_types": ["VAT"],
                                               "tax_period": "2026"}, headers=A).json()["id"]
    facts = {"material_facts": "Bán máy tính trong nước",
             "case_facts": {"goods_description": "Máy tính", "transaction_type": "Bán trong nước",
                            "transaction_date": "2026-03"}}
    asks = {"draft": {"question": "Mức thuế suất 10% áp dụng cho hàng hóa nào?", "tax_type": "VAT", **facts},
            "clarify": {"question": "Mức thuế suất 10% áp dụng cho hàng hóa nào?", "tax_type": "VAT"},
            "abstain": {"question": "quy định về hóa đơn điện tử", "tax_type": "CIT", **facts}}   # không có nguồn
    saved = {}
    for status, body in asks.items():
        r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, **body}).json()
        assert r["research_result"]["status"] == status, (status, r["research_result"])
        saved[r["history"]["id"]] = r["research_result"]
    reopened = {h["id"]: h["research_result"]
                for h in client.get(f"/api/v1/matters/{mid}/history", headers=A).json()}
    assert reopened == saved
    for result in saved.values():
        assert set(result) == {"status", "sections", "clarification_questions", "warnings"}
        assert set(result["sections"]) == {"issue", "facts", "authority", "analysis", "limitations", "next_steps"}
