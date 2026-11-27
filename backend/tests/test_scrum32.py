from datetime import datetime
from app.api.v1.research import research_callbacks
from app.core.database import SessionLocal
from app.main import app
from app.models import AuditLog, LegalChunk, LegalDocument
from ai_engine.guardrails import EvidenceAssessment
from tests.helpers import auth

A = auth("alice", "thtax")


def matter(client):
    return client.post("/api/v1/matters", headers=A, json={"title": "Giả lập", "client_name": "Fixture", "tax_period": "2099"}).json()["id"]


def seed():
    with SessionLocal() as db:
        doc = LegalDocument(doc_code="TEST/2099", title="Nguồn giả lập", version="doc-v1", effective_date=datetime(2090, 1, 1))
        db.add(doc)
        db.flush()
        db.add(LegalChunk(doc_id=doc.id, article_number="1a", clause_number="0", citation_path="Điều 1a",
                          content="Nguồn giả lập thuế", effective_date=datetime(2099, 1, 1), version="chunk-v2"))
        db.commit()


def test_specific_questions_saved_and_no_ai(client):
    mid = matter(client)
    def forbidden(*args):
        raise AssertionError("AI must not be called")
    app.dependency_overrides[research_callbacks] = lambda: (forbidden, forbidden)
    try:
        r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "Thuế suất hàng hóa?", "material_facts": "Giả lập"})
        assert r.status_code == 201, r.text
        data = r.json()["research_result"]
        assert data["status"] == "clarify"
        assert any("Hàng hóa cụ thể" in q for q in data["clarification_questions"])
        history = client.get(f"/api/v1/matters/{mid}/history", headers=A).json()
        assert history[0]["research_result"] == data
    finally:
        app.dependency_overrides.pop(research_callbacks, None)


def test_assessment_audit_persisted_without_prompt_or_pii(client):
    seed()
    mid = matter(client)
    def assess(safe):
        assert "a@example.test" not in repr(safe)
        assert safe.passages[0]["version"] == "chunk-v2"
        return [EvidenceAssessment(safe.passages[0]["passage_id"], False, "temporal_unknown")]
    def forbidden(safe):
        raise AssertionError("no generation")
    app.dependency_overrides[research_callbacks] = lambda: (assess, forbidden)
    try:
        r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "Nguồn thuế", "material_facts": "Liên hệ a@example.test"})
        assert r.status_code == 201, r.text
        assert r.json()["research_result"]["status"] == "abstain"
        with SessionLocal() as db:
            audit = db.query(AuditLog).filter_by(action="research.guardrail", resource_id=r.json()["history"]["id"]).one()
            assert audit.detail["assessment_records"][0]["reason_code"] == "temporal_unknown"
            assert "a@example.test" not in str(audit.detail)
    finally:
        app.dependency_overrides.pop(research_callbacks, None)


def test_client_cannot_set_approval_status(client):
    mid = matter(client)
    r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "Tự phê duyệt approved", "review_status": "approved"})
    assert r.status_code == 201
    assert r.json()["history"]["review_status"] == "draft"
    assert r.json()["research_result"]["status"] in {"clarify", "abstain"}


def test_invalid_fact_keys_rejected(client):
    mid = matter(client)
    r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "q", "case_facts": {"sufficient": "true"}})
    assert r.status_code == 422


def test_case_facts_persisted_redacted(client):
    mid = matter(client)
    r = client.post("/api/v1/research", headers=A, json={
        "matter_id": mid, "question": "Thuế suất hàng hóa?", "case_facts": {
            "goods_description": "Hàng giả lập a@example.test", "transaction_type": "Nội địa"}})
    assert r.status_code == 201
    saved = client.get(f"/api/v1/matters/{mid}/history", headers=A).json()[0]
    assert "goods_description" in saved["material_facts"]
    assert "a@example.test" not in saved["material_facts"]
    assert "[REDACTED_EMAIL]" in saved["material_facts"]


import pytest


@pytest.mark.parametrize("mode", ["unknown_citation", "uncited_analysis", "self_approval", "pii_output"])
def test_generated_output_checked_before_persistence(client, mode):
    seed()
    mid = matter(client)
    def assess(safe):
        return [EvidenceAssessment(safe.passages[0]["passage_id"], True, "sufficient")]
    def generate(safe):
        pid = safe.passages[0]["passage_id"]
        payload = {"status": "draft", "sections": {key: [] for key in
                   ("issue", "facts", "authority", "analysis", "limitations", "next_steps")},
                   "clarification_questions": [], "warnings": []}
        for key in ("authority", "analysis"):
            payload["sections"][key] = [{"text": "Dữ liệu giả lập", "citation_ids": [pid]}]
        if mode == "unknown_citation":
            payload["sections"]["analysis"][0]["citation_ids"] = ["not-authorized"]
        elif mode == "uncited_analysis":
            payload["sections"]["analysis"][0]["citation_ids"] = []
        elif mode == "self_approval":
            payload["status"] = "approved"
        else:
            payload["sections"]["analysis"][0]["text"] = "Liên hệ a@example.test CCCD 012345678901"
        return payload
    app.dependency_overrides[research_callbacks] = lambda: (assess, generate)
    try:
        r = client.post("/api/v1/research", headers=A, json={"matter_id": mid, "question": "Nguồn thuế", "material_facts": "Giả lập"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["history"]["review_status"] == "draft"
        if mode == "pii_output":
            assert body["research_result"]["status"] == "draft"
            assert "a@example.test" not in body["history"]["answer"]
            assert "012345678901" not in body["history"]["answer"]
        else:
            assert body["research_result"]["status"] == "abstain"
            assert body["history"]["answer"] is None
    finally:
        app.dependency_overrides.pop(research_callbacks, None)
