"""
tests/test_sources_research.py  –  XÁC THỰC, QUYỀN HỒ SƠ, TÌM NGUỒN LUẬT, TRA CỨU + LƯU LỊCH SỬ
=============================================================================================
Dữ liệu luật mẫu được nạp thẳng vào bảng legal_documents / legal_chunks (như nhóm Data sẽ làm).
"""
from datetime import datetime

import pytest

from app.core.database import SessionLocal
from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from tests.helpers import auth

A = auth("alice", "thtax")
B = auth("bob", "other")


@pytest.fixture()
def seeded(client):
    """2 văn bản: Luật GTGT mới (hiệu lực 2026) và Thông tư cũ đã hết hiệu lực cuối 2025."""
    with SessionLocal() as db:
        law = LegalDocument(doc_code="48/2024/QH15", title="Luật Thuế giá trị gia tăng", doc_type="LUAT",
                            hierarchy_level=1, effective_date=datetime(2025, 7, 1), version="1.0",
                            source_url="https://vbpl.vn/48-2024-qh15")
        old = LegalDocument(doc_code="219/2013/TT-BTC", title="Thông tư hướng dẫn thuế GTGT", doc_type="THONG_TU",
                            hierarchy_level=3, effective_date=datetime(2014, 1, 1),
                            expiry_date=datetime(2025, 7, 1), version="1.0")
        db.add_all([law, old])
        db.flush()
        db.add_all([LegalDocumentTaxScope(doc_id=law.id, tax_type="VAT"),
                    LegalDocumentTaxScope(doc_id=old.id, tax_type="VAT")])
        c1 = LegalChunk(doc_id=law.id, article_number="9", article_title="Thuế suất", clause_number=1,
                        point_letter="", citation_path="Khoản 1, Điều 9, 48/2024/QH15", hierarchy_level=1,
                        content="Khoản 1, Điều 9, 48/2024/QH15: Thuế suất 0% áp dụng đối với hàng hóa xuất khẩu.")
        c2 = LegalChunk(doc_id=law.id, article_number="9", article_title="Thuế suất", clause_number=3,
                        point_letter="a", citation_path="Điểm a, Khoản 3, Điều 9, 48/2024/QH15", hierarchy_level=1,
                        content="Điểm a, Khoản 3, Điều 9, 48/2024/QH15: Thuế suất 10% là mức phổ thông.")
        c3 = LegalChunk(doc_id=old.id, article_number="11", clause_number=0, point_letter="",
                        citation_path="Điều 11, 219/2013/TT-BTC", hierarchy_level=3,
                        content="Điều 11, 219/2013/TT-BTC: Thuế suất 10% phổ thông (văn bản cũ).")
        db.add_all([c1, c2, c3])
        db.commit()
        return {"export": str(c1.id), "standard": str(c2.id), "old": str(c3.id)}


def _matter(client, headers=A) -> str:
    r = client.post("/api/v1/matters", json={"title": "Hồ sơ", "client_name": "ABC", "tax_period": "2026"},
                    headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ----------------------------- XÁC THỰC -----------------------------
@pytest.mark.parametrize("path", ["/api/v1/matters", "/api/v1/sources/search?q=x", "/api/v1/sources/1"])
def test_missing_or_wrong_token_is_401(client, path):
    assert client.get(path).status_code == 401
    r = client.get(path, headers={"Authorization": "Bearer wrong-token-xxxxxxxx"})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_research_requires_token(client):
    assert client.post("/api/v1/research", json={"matter_id": _matter(client), "question": "x"}).status_code == 401


def test_old_self_declared_headers_no_longer_work(client):
    # Trước đây client tự khai X-Tenant-Id; nay phải bị từ chối
    assert client.get("/api/v1/matters", headers={"X-User-Id": "alice", "X-Tenant-Id": "thtax"}).status_code == 401


def test_health_stays_public(client):
    assert client.get("/health").status_code == 200


def test_tenant_comes_from_token(client):
    r = client.post("/api/v1/matters", json={"title": "t", "client_name": "c"},
                    headers={**A, "X-Tenant-Id": "other"})  # header giả mạo bị bỏ qua
    assert r.json()["tenant_id"] == "thtax" and r.json()["created_by"] == "alice"


# --------------------------- QUYỀN HỒ SƠ ----------------------------
def test_archived_matter_is_read_only(client):
    mid = _matter(client)
    client.delete(f"/api/v1/matters/{mid}", headers=A)
    assert client.patch(f"/api/v1/matters/{mid}", json={"title": "x"}, headers=A).status_code == 409
    assert client.post(f"/api/v1/matters/{mid}/history", json={"question": "x"}, headers=A).status_code == 409
    assert client.post("/api/v1/research", json={"matter_id": mid, "question": "x"}, headers=A).status_code == 409
    assert client.get(f"/api/v1/matters/{mid}/history", headers=A).status_code == 200  # vẫn xem được


def test_research_on_other_tenant_matter_is_404(client, seeded):
    mid = _matter(client)
    r = client.post("/api/v1/research", json={"matter_id": mid, "question": "thuế suất"}, headers=B)
    assert r.status_code == 404
    assert client.get(f"/api/v1/matters/{mid}/history", headers=A).headers["X-Total-Count"] == "0"


# ------------------------------ NGUỒN -------------------------------
def test_search_returns_matching_passages_with_metadata(client, seeded):
    r = client.get("/api/v1/sources/search", params={"q": "thuế suất phổ thông"}, headers=A)
    assert r.status_code == 200
    ids = [h["source_id"] for h in r.json()]
    # BM25 relevance is not legal hierarchy; all three contain matching words.
    assert set(ids) == set(seeded.values())
    top = next(h for h in r.json() if h["source_id"] == seeded["standard"])
    assert top["legal_identifier"] == "48/2024/QH15" and top["dieu"] == "9" and top["khoan"] == "3"
    assert top["diem"] == "a" and top["doc_type"] == "LUAT" and top["url"].startswith("https://")


def test_search_filters_as_of_and_doc_type(client, seeded):
    hits = client.get("/api/v1/sources/search", params={"q": "phổ thông", "as_of": "2026-01-01"}, headers=A).json()
    assert [h["source_id"] for h in hits] == [seeded["standard"]]  # thông tư hết hiệu lực bị loại
    hits = client.get("/api/v1/sources/search", params={"q": "phổ thông", "as_of": "2020-01-01"}, headers=A).json()
    assert [h["source_id"] for h in hits] == [seeded["old"]]       # luật chưa có hiệu lực bị loại
    hits = client.get("/api/v1/sources/search", params={"q": "phổ thông", "doc_type": "thong_tu"}, headers=A).json()
    assert [h["source_id"] for h in hits] == [seeded["old"]]


def test_search_wildcards_are_literal_and_validation(client, seeded):
    assert client.get("/api/v1/sources/search", params={"q": "%"}, headers=A).json() == []
    assert client.get("/api/v1/sources/search", params={"q": "_"}, headers=A).json() == []
    assert client.get("/api/v1/sources/search", params={"q": ""}, headers=A).status_code == 422
    assert client.get("/api/v1/sources/search", params={"q": "x", "limit": 51}, headers=A).status_code == 422


def test_get_source_detail(client, seeded):
    r = client.get(f"/api/v1/sources/{seeded['standard']}", headers=A)
    assert r.status_code == 200
    assert r.json()["content"].endswith("mức phổ thông.") and r.json()["article_title"] == "Thuế suất"
    assert client.get("/api/v1/sources/999999", headers=A).status_code == 404
    assert client.get("/api/v1/sources/abc", headers=A).status_code == 422


# ----------------------------- TRA CỨU ------------------------------
def test_research_saves_history_with_citations(client, seeded):
    mid = _matter(client)
    body = {"matter_id": mid, "question": "  Thuế suất phổ thông là bao nhiêu?  ", "tax_type": "VAT",
            "research_as_of": "2026-03-15", "limit": 5}
    r = client.post("/api/v1/research", json=body, headers=A)
    assert r.status_code == 201, r.text
    data = r.json()
    assert seeded["standard"] in [s["source_id"] for s in data["sources"]]
    assert seeded["old"] not in [s["source_id"] for s in data["sources"]]  # hết hiệu lực tại 2026-03-15
    h = data["history"]
    assert h["question"] == "Thuế suất phổ thông là bao nhiêu?" and h["tax_period"] == "2026"
    assert h["research_as_of"] == "2026-03-15" and h["answer"] is None and h["actor"] == "alice"
    assert [c["source_id"] for c in h["citations"]] == [s["source_id"] for s in data["sources"]]
    assert h["warnings"] and h["review_status"] == "draft"

    saved = client.get(f"/api/v1/matters/{mid}/history", headers=A)
    assert saved.headers["X-Total-Count"] == "1" and saved.json()[0]["id"] == h["id"]
    # citation lưu trong lịch sử mở được nguyên văn qua /sources/{id}
    assert client.get(f"/api/v1/sources/{h['citations'][0]['source_id']}", headers=A).status_code == 200


def test_research_without_sources_abstains(client, seeded):
    mid = _matter(client)
    r = client.post("/api/v1/research", json={"matter_id": mid, "question": "xyzabc"}, headers=A)
    assert r.status_code == 201
    assert r.json()["sources"] == [] and r.json()["history"]["citations"] == []
    assert "Không tìm thấy căn cứ" in r.json()["history"]["warnings"][0]


def test_research_validation(client):
    mid = _matter(client)
    for bad in ({"matter_id": mid, "question": "   "}, {"matter_id": "not-uuid", "question": "x"},
                {"matter_id": mid, "question": "x", "research_as_of": "15/03/2026"}):
        assert client.post("/api/v1/research", json=bad, headers=A).status_code == 422
    missing = {"matter_id": "00000000-0000-0000-0000-000000000000", "question": "x"}
    assert client.post("/api/v1/research", json=missing, headers=A).status_code == 404
