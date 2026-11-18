import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import LegalDocument, LegalChunk, LegalDocumentTaxScope
from app.schemas.ingestion import ImportInput, legal_date
from app.services.legal_ingestion_service import ingest_legal_document
from app.services.source_service import search, to_detail
from backend.scripts.export_bm25_retrieval import retrieve_benchmark
from data_pipeline.parser.chunker import chunk_legal_document
from tests.helpers import auth


@pytest.fixture
def payload():
    return {
        "document": {"doc_code": "FIXTURE-IMPORT", "title": "Synthetic document",
                     "doc_type": "LUAT", "hierarchy_level": 1,
                     "effective_date": "2024-01-01", "expiry_date": "2025-01-01"},
        "chunks": [{"article_number": "1a", "clause_number": "1a", "point_letter": "",
                    "content": "Intro and fixture_tax evidence.", "citation_path": "Fixture 1a",
                    "article_intro": "Intro", "clause_intro": "", "source_page": 2,
                    "hierarchy_level": 1, "doc_type": "LUAT", "source_url": None,
                    "effective_date": "2024-01-01", "expiry_date": "2025-01-01",
                    "status": "CON_HIEU_LUC", "version": "1.0",
                    "amends_doc_code": None, "replaces_doc_code": None}],
        "as_of": "2025-01-01", "tax_types": ["VAT", "VAT"],
    }


def test_import_round_trip_and_exclusive_expiry(client, payload):
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
        assert receipt.temporal_status == "HET_HIEU_LUC"
    with SessionLocal() as db:
        row = db.get(LegalChunk, receipt.chunk_ids[0])
        assert to_detail(row).khoan == "1a"
        assert to_detail(row).dieu == "1a"
        assert to_detail(row).content == payload["chunks"][0]["content"]
        assert db.scalar(select(func.count()).select_from(LegalDocumentTaxScope)) == 1
        assert search(db, "fixture_tax", as_of=date(2024, 12, 31))
        assert search(db, "fixture_tax", as_of=date(2025, 1, 1)) == []
        assert search(db, "fixture_tax", as_of=date(2026, 1, 1), tax_period="2024", tax_type="VAT")


def test_public_excerpt_search_and_recall_share_passage_ids(client):
    fixture = Path(__file__).parent / "fixtures" / "public_law_excerpt.json"
    excerpt = json.loads(fixture.read_text(encoding="utf-8"))
    document = {key: excerpt[key] for key in (
        "doc_code", "title", "doc_type", "hierarchy_level", "source_url", "effective_date", "expiry_date"
    )}
    document["version"] = "pilot-excerpt-1"
    chunks = chunk_legal_document(
        excerpt["text"], document["doc_code"], document["hierarchy_level"], excerpt["pdf_page"], document
    )
    assert [chunk["article_number"] for chunk in chunks] == excerpt["expected_articles"]
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, {
            "document": document, "chunks": chunks, "tax_types": ["VAT"], "as_of": "2026-11-14",
        })

    headers = auth("alice", "thtax")
    response = client.get("/api/v1/sources/search", headers=headers, params={
        "q": excerpt["query"], "tax_type": "VAT", "as_of": "2026-11-14",
    })
    assert response.status_code == 200
    hits = response.json()
    top = hits[0]
    assert top["source_id"] == str(receipt.chunk_ids[0])
    assert top["legal_identifier"] == document["doc_code"]
    assert (top["dieu"], top["khoan"], top["diem"]) == ("1", None, None)
    assert top["url"] == document["source_url"]
    assert top["source_page"] == excerpt["pdf_page"]
    assert top["version"] == document["version"]
    assert top["effective_date"] is None and top["expiry_date"] is None
    detail = client.get(f"/api/v1/sources/{top['source_id']}", headers=headers)
    assert detail.json()["content"] == chunks[0]["content"]

    with SessionLocal() as db:
        results = retrieve_benchmark(db, {"cases": [
            {"case_id": "PUBLIC-EXCERPT", "answerability": "answerable", "category": "VAT",
             "question": excerpt["query"], "research_as_of": "2026-11-14"},
        ]})
    assert results == [{"case_id": "PUBLIC-EXCERPT", "retrieved_passage_ids": [hit["source_id"] for hit in hits]}]


def test_recall_export_takes_top_ten_after_tax_and_period_filters(client, payload):
    chunk = payload["chunks"][0]
    payload["chunks"] = [dict(chunk, article_number=str(i), citation_path=f"Điều {i}") for i in range(1, 13)]
    other = deepcopy(payload)
    other["document"]["doc_code"] = "FIXTURE-CIT"
    other["tax_types"] = ["CIT"]

    with SessionLocal.begin() as db:
        ingest_legal_document(db, other)
        receipt = ingest_legal_document(db, payload)

    case = {"case_id": "HISTORY", "answerability": "answerable", "category": "VAT",
            "question": "fixture_tax", "tax_period": "2024", "research_as_of": "2026-11-14"}
    expected_ids = [str(chunk_id) for chunk_id in receipt.chunk_ids[:10]]
    response = client.get("/api/v1/sources/search", headers=auth("alice", "thtax"), params={
        "q": case["question"], "tax_type": "VAT", "tax_period": "2024", "as_of": "2026-11-14",
    })
    assert response.status_code == 200
    assert [hit["source_id"] for hit in response.json()] == expected_ids

    with SessionLocal() as db:
        results = retrieve_benchmark(db, {"cases": [case]})
        assert results == [{"case_id": "HISTORY", "retrieved_passage_ids": expected_ids}]
        case["tax_period"] = None
        assert retrieve_benchmark(db, {"cases": [case]})[0]["retrieved_passage_ids"] == []


@pytest.mark.parametrize("clause", [None, "", " ", 0, "0"])
def test_absent_clause_maps_to_null_in_api(client, payload, clause):
    payload["chunks"][0]["clause_number"] = clause
    with SessionLocal.begin() as db:
        result = ingest_legal_document(db, payload)
    with SessionLocal() as db:
        assert to_detail(db.get(LegalChunk, result.chunk_ids[0])).khoan is None


@pytest.mark.parametrize("field", ["issue_date", "effective_date", "expiry_date"])
@pytest.mark.parametrize("bad", ["invalid", "", "2024-02-30", "01/01/2024", 1700000000, True])
def test_invalid_document_date_writes_nothing(client, payload, field, bad):
    payload["document"][field] = bad
    with SessionLocal() as db:
        with pytest.raises(ValidationError):
            ingest_legal_document(db, payload)
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0
        assert db.scalar(select(func.count()).select_from(LegalChunk)) == 0


@pytest.mark.parametrize("expiry", ["2023-12-31", "2024-01-01"])
def test_inverted_or_empty_interval_rejected(client, payload, expiry):
    payload["document"]["expiry_date"] = expiry
    with SessionLocal() as db, pytest.raises(ValidationError):
        ingest_legal_document(db, payload)


def test_bad_second_chunk_does_not_partially_import(client, payload):
    bad = deepcopy(payload["chunks"][0])
    bad["expiry_date"] = "invalid"
    payload["chunks"].append(bad)
    with SessionLocal() as db:
        with pytest.raises(ValidationError):
            ingest_legal_document(db, payload)
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0


def test_conflicting_chunk_metadata_rejected(client, payload):
    payload["chunks"][0]["effective_date"] = "2024-02-01"
    with SessionLocal() as db, pytest.raises(ValidationError):
        ingest_legal_document(db, payload)


def test_duplicate_preserves_ids_and_content(client, payload):
    with SessionLocal.begin() as db:
        first = ingest_legal_document(db, payload)
    payload["chunks"][0]["content"] = "Changed content must not overwrite citation."
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="Mã văn bản"):
            ingest_legal_document(db, payload)
        assert db.get(LegalChunk, first.chunk_ids[0]).content == "Intro and fixture_tax evidence."
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 1


def test_caller_can_rollback_import(client, payload):
    with SessionLocal() as db:
        ingest_legal_document(db, payload)
        db.rollback()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0


@pytest.mark.parametrize("as_of,expected", [("2023-12-31", "CHUA_XAC_DINH"),
                                          ("2024-01-01", "CON_HIEU_LUC"),
                                          ("2025-01-01", "HET_HIEU_LUC"),
                                          ("2025-01-02", "HET_HIEU_LUC")])
def test_temporal_status_does_not_trust_parser(client, payload, as_of, expected):
    payload["as_of"] = as_of
    payload["chunks"][0]["status"] = "CON_HIEU_LUC"
    with SessionLocal.begin() as db:
        assert ingest_legal_document(db, payload).temporal_status == expected


def test_missing_dates_remain_unknown(client, payload):
    for obj in [payload["document"], payload["chunks"][0]]:
        obj["effective_date"] = obj["expiry_date"] = None
    with SessionLocal.begin() as db:
        result = ingest_legal_document(db, payload)
        assert result.temporal_status == "CHUA_XAC_DINH"
        assert db.get(LegalDocument, result.document_id).expiry_date is None


def test_parser_naive_midnight_datetime_is_accepted(payload):
    payload["document"]["effective_date"] = datetime(2024, 1, 1)
    assert ImportInput.model_validate(payload).document.effective_date == date(2024, 1, 1)


@pytest.mark.parametrize("value", ["2024-01-01T00:00:00Z", datetime(2024, 1, 1, 12)])
def test_times_are_not_silently_truncated(value):
    with pytest.raises(ValueError):
        legal_date(value)
