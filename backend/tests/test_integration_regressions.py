"""Isolated fixtures: structural behavior, not approved legal conclusions."""
from datetime import datetime

import pytest
from app.core.database import SessionLocal
from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from app.main import app
from app.api.v1.research import research_callbacks
from app.services.legal_metadata import clause_label, period_bounds
from app.services.guarded_research_service import research_from_rows
from ai_engine.guardrails import EvidenceAssessment, Claim, GeneratedResearch
from tests.helpers import auth

HEADERS = auth("alice", "thtax")


@pytest.fixture()
def corpus(client):
    ids = {}
    with SessionLocal() as db:
        for code, tax, start, end, clause in [
            ("OLD", "VAT", datetime(2020, 1, 1), datetime(2025, 1, 1), "1a"),
            ("NEW", "VAT", datetime(2025, 1, 1), None, "0"),
            ("CIT", "CIT", datetime(2020, 1, 1), None, "2"),
            ("UNKNOWN", None, None, None, "0"),
        ]:
            d = LegalDocument(doc_code=code, title="Synthetic fixture", doc_type="LUAT",
                              hierarchy_level=1, effective_date=start, expiry_date=end)
            db.add(d); db.flush()
            if tax:
                db.add(LegalDocumentTaxScope(doc_id=d.id, tax_type=tax))
            c = LegalChunk(doc_id=d.id, article_number="1a", clause_number=clause,
                           citation_path="Fixture", content="fixture_tax evidence", hierarchy_level=1)
            db.add(c); db.flush(); ids[code] = str(c.id)
        db.commit()
    return ids


def matter(client, period="2024"):
    return client.post("/api/v1/matters", headers=HEADERS,
                       json={"title": "fixture", "client_name": "synthetic", "tax_period": period}).json()["id"]


def test_historical_period_overrides_research_date_and_filters_tax(client, corpus):
    r = client.post("/api/v1/research", headers=HEADERS, json={
        "matter_id": matter(client), "question": "fixture_tax", "tax_type": "VAT",
        "research_as_of": "2026-11-14", "material_facts": "Synthetic transaction"})
    assert r.status_code == 201
    assert [h["source_id"] for h in r.json()["sources"]] == [corpus["OLD"]]
    assert r.json()["sources"][0]["khoan"] == "1a"
    assert r.json()["research_result"]["status"] == "abstain"  # no assessor configured
    assert r.json()["history"]["answer"] is None


def test_filter_tax_excludes_other_tax_and_unclassified(client, corpus):
    r = client.get("/api/v1/sources/search", headers=HEADERS,
                   params={"q": "fixture_tax", "tax_type": "CIT", "tax_period": "2024"})
    assert [h["source_id"] for h in r.json()] == [corpus["CIT"]]


def test_zero_clause_and_alphanumeric_detail(client, corpus):
    assert client.get('/api/v1/sources/'+corpus['NEW'], headers=HEADERS).json()['khoan'] is None
    assert client.get('/api/v1/sources/'+corpus['OLD'], headers=HEADERS).json()['khoan'] == '1a'
    with SessionLocal() as db:
        c = db.get(LegalChunk, int(corpus['NEW']))
        seen = []
        def assess(safe):
            seen.append(safe.passages[0]['khoan'])
            return []
        research_from_rows('fixture_tax', [(c, 1)], tax_period='2026', material_facts='fixture', assess=assess)
        assert seen == [None]


@pytest.mark.parametrize('value', [0, '0', '', ' ', None])
def test_zero_sentinel(value):
    assert clause_label(value) is None


@pytest.mark.parametrize('period', ['2024-13', '0000', 'last year', '2024-Q5'])
def test_invalid_period_is_422(client, period):
    r = client.post('/api/v1/research', headers=HEADERS, json={
        'matter_id': matter(client), 'question': 'fixture', 'tax_period': period})
    assert r.status_code == 422


def test_period_boundaries():
    assert period_bounds('2024-02')[1].day == 29
    assert period_bounds('2024-Q2')[0].month == 4
    assert period_bounds('2024-Q2')[1].month == 6


def test_guardrails_missing_facts_and_redacted_history(client, corpus):
    r = client.post('/api/v1/research', headers=HEADERS, json={
        'matter_id': matter(client), 'question': 'fixture_tax email alice@example.com'})
    assert r.json()['research_result']['status'] == 'clarify'
    assert r.json()['research_result']['clarification_questions']
    assert 'alice@example.com' not in r.json()['history']['question']


@pytest.mark.parametrize('invalid_citation', [False, True])
def test_endpoint_generator_citations_and_history(client, corpus, invalid_citation):
    def assess(safe):
        return [EvidenceAssessment(passage_id=safe.passages[0]['passage_id'], sufficient=True)]
    def generate(safe):
        pid = 'not-retrieved' if invalid_citation else safe.passages[0]['passage_id']
        return GeneratedResearch((Claim('Fixture authority', (pid,), 'authority'),
                                  Claim('Fixture analysis', (pid,), 'analysis')))
    app.dependency_overrides[research_callbacks] = lambda: (assess, generate)
    try:
        mid = matter(client)
        data = client.post('/api/v1/research', headers=HEADERS, json={
            'matter_id': mid, 'question': 'fixture_tax', 'tax_type': 'VAT',
            'material_facts': 'Synthetic facts'}).json()
        assert data['research_result']['status'] == ('abstain' if invalid_citation else 'draft')
        if invalid_citation:
            assert data['history']['answer'] is None
        else:
            assert [c['source_id'] for c in data['history']['citations']] == [corpus['OLD']]
            saved = client.get(f'/api/v1/matters/{mid}/history', headers=HEADERS).json()[0]
            assert saved['answer'] == data['history']['answer']
        assert data['history']['review_status'] == 'draft'
    finally:
        app.dependency_overrides.pop(research_callbacks, None)
