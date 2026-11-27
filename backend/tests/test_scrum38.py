"""API + actual callback paths + simulated HTTP provider; never external traffic."""
import json
from datetime import datetime

import httpx
import pytest

from ai_engine.providers import chat_json
from ai_engine.synthesis.backend_adapter import make_guarded_generator
from app.api.v1 import research as route
from app.core.database import SessionLocal
from app.models import AuditLog, LegalChunk, LegalDocument
from tests.helpers import auth

AUTH = auth("alice", "thtax")


def setup_provider(client, monkeypatch, mode):
    monkeypatch.setenv("RESEARCH_AI_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_AI_URL", "https://provider.example.test/chat/completions")
    monkeypatch.setenv("RESEARCH_AI_MODEL", "test-model")
    monkeypatch.setenv("RESEARCH_AI_API_KEY", "secret-test-token-only")
    mid = client.post("/api/v1/matters", headers=AUTH, json={"title": "Fixture", "client_name": "Fixture", "tax_period": "2099"}).json()["id"]
    with SessionLocal() as db:
        doc = LegalDocument(doc_code="TEST/2099", title="Nguồn giả lập", effective_date=datetime(2099, 1, 1))
        db.add(doc)
        db.flush()
        chunk = LegalChunk(doc_id=doc.id, article_number="1", clause_number="0", content="Nguồn thuế giả lập",
                           citation_path="Điều 1 TEST/2099", effective_date=datetime(2099, 1, 1),
                           status="CON_HIEU_LUC", version="fixture-only")
        db.add(chunk)
        db.commit()
        pid = str(chunk.id)
    calls = []
    def handler(request):
        sent = json.loads(request.content)
        calls.append(sent)
        assert "a@example.test" not in request.content.decode()
        if mode == "timeout":
            raise httpx.ReadTimeout("secret-test-token-only a@example.test")
        if mode == "auth":
            return httpx.Response(401, text="secret-test-token-only a@example.test")
        if mode == "malformed":
            return httpx.Response(200, text="not JSON a@example.test")
        if len(calls) == 1:
            result = {"context_complete": mode != "missing_facts", "query_supported": mode != "insufficient", "conflicts_resolved": True,
                      "assessments": [{"passage_id": pid, "sufficient": True, "reason_code": "sufficient"}]}
        else:
            result = {"status": "approved" if mode == "approved" else "draft", "sections": {
                key: [] for key in ("issue", "facts", "authority", "analysis", "limitations", "next_steps")},
                "warnings": [], "clarification_questions": []}
            for key in ("authority", "analysis"):
                result["sections"][key] = [{"text": "Nội dung giả lập a@example.test", "citation_ids": [pid]}]
            if mode == "unknown_id":
                result["sections"]["analysis"][0]["citation_ids"] = ["unknown-source"]
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})
    original_client = httpx.Client
    def local_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(**kwargs)
    monkeypatch.setattr(chat_json.httpx, "Client", local_client)
    # Resolve the exact server callback paths from documented config, no public request flags.
    monkeypatch.setattr(route, "_ASSESS", route._load("ai_engine.guardrails.llm_assessor:assess"))
    monkeypatch.setattr(route, "_GENERATE", make_guarded_generator(route._load("ai_engine.providers.chat_json:complete")))
    return mid, calls


@pytest.mark.parametrize("mode,expected,calls_expected", [
    ("draft", "draft", 2), ("missing_facts", "clarify", 1), ("insufficient", "abstain", 1), ("unknown_id", "abstain", 2),
    ("approved", "abstain", 2), ("timeout", "abstain", 1), ("auth", "abstain", 1), ("malformed", "abstain", 1),
])
def test_provider_callbacks_api_and_audit(client, monkeypatch, mode, expected, calls_expected):
    mid, calls = setup_provider(client, monkeypatch, mode)
    r = client.post("/api/v1/research", headers=AUTH, json={"matter_id": mid, "question": "Nguồn thuế a@example.test", "material_facts": "Giả lập"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["research_result"]["status"] == expected
    assert body["history"]["review_status"] == "draft"
    assert len(calls) == calls_expected
    assert "secret-test-token-only" not in r.text and "a@example.test" not in r.text
    if expected == "abstain":
        assert body["history"]["answer"] is None
    with SessionLocal() as db:
        audit = db.query(AuditLog).filter_by(action="research.guardrail", resource_id=body["history"]["id"]).one()
        assert audit.detail["status"] == expected
        assert "secret-test-token-only" not in repr(audit.detail)
        assert "a@example.test" not in repr(audit.detail)
        if mode in ("timeout", "auth", "malformed"):
            assert audit.detail["reason"] in {"provider_timeout", "provider_auth", "provider_invalid_output"}
    saved = client.get(f"/api/v1/matters/{mid}/history", headers=AUTH).json()[0]
    assert saved["research_result"] == body["research_result"]


def test_clarification_does_not_call_provider(client, monkeypatch):
    mid, calls = setup_provider(client, monkeypatch, "draft")
    r = client.post("/api/v1/research", headers=AUTH, json={"matter_id": mid, "question": "Thuế suất GTGT hàng hóa?", "material_facts": "Giả lập"})
    assert r.status_code == 201
    assert r.json()["research_result"]["status"] == "clarify"
    assert not calls


def test_disabled_provider_fails_closed(client, monkeypatch):
    mid, calls = setup_provider(client, monkeypatch, "draft")
    monkeypatch.setenv("RESEARCH_AI_ENABLED", "false")
    r = client.post("/api/v1/research", headers=AUTH, json={"matter_id": mid, "question": "Nguồn thuế", "material_facts": "Giả lập"})
    assert r.status_code == 201
    assert r.json()["research_result"]["status"] == "abstain"
    assert not calls
