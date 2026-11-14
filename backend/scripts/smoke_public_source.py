"""Explicitly opt-in smoke test for an isolated PostgreSQL integration DB.

Uses actual extracted legislation; tests data flow, not legal correctness.
Run inside the backend container; provide SMOKE_API_TOKEN (local test only).
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import LegalDocument, LegalChunk
from app.services.legal_ingestion_service import ingest_legal_document
from data_pipeline.parser.chunker import chunk_legal_document


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--confirm-test-database", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--fixture", type=Path,
                        default=Path(__file__).resolve().parents[1] / "tests/fixtures/public_law_excerpt.json")
    args = parser.parse_args()
    database = make_url(settings.database_url)
    if database.get_backend_name() != "postgresql" or database.database != args.confirm_test_database:
        raise SystemExit("Refusing write: confirm the isolated PostgreSQL test database name.")
    token = os.environ["SMOKE_API_TOKEN"]
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    metadata = {k: fixture[k] for k in ("doc_type", "effective_date", "expiry_date")}
    metadata.update(source_url=fixture["source_url"], version="pilot-excerpt-1")
    chunks = chunk_legal_document(fixture["text"], fixture["doc_code"],
                                  fixture["hierarchy_level"], fixture["pdf_page"], metadata)
    assert [c["article_number"] for c in chunks] == fixture["expected_articles"]
    document = {k: fixture[k] for k in ("doc_code", "title", "doc_type", "hierarchy_level",
                                       "source_url", "effective_date", "expiry_date")}
    document["version"] = "pilot-excerpt-1"
    with SessionLocal.begin() as db:
        existing = db.scalar(select(LegalDocument).where(LegalDocument.doc_code == fixture["doc_code"]))
        if existing is None:
            receipt = ingest_legal_document(db, {"document": document, "chunks": chunks,
                                                "tax_types": [fixture["tax_type"]], "as_of": "2026-11-14"})
            chunk_ids = list(receipt.chunk_ids)
        else:
            rows = list(db.scalars(select(LegalChunk).where(LegalChunk.doc_id == existing.id)
                                   .order_by(LegalChunk.id)))
            assert [r.content for r in rows] == [c["content"] for c in chunks], "Existing data differs; no overwrite."
            chunk_ids = [r.id for r in rows]
    with httpx.Client(base_url=args.base_url, headers={"Authorization": f"Bearer {token}"}, timeout=20) as api:
        assert api.get("/health").json()["database"] is True
        with httpx.Client(base_url=args.base_url, timeout=20) as anonymous:
            assert anonymous.get("/api/v1/matters").status_code == 401
        created = api.post("/api/v1/matters", json={"title": "SCRUM-24 public-source smoke",
                           "client_name": "SYNTHETIC TEST MATTER", "tax_types": ["VAT"], "tax_period": "2026"})
        assert created.status_code == 201, created.text
        mid = created.json()["id"]
        response = api.post("/api/v1/research", json={"matter_id": mid, "question": fixture["query"],
                            "tax_type": "VAT", "tax_period": "2026", "research_as_of": "2026-11-14",
                            "material_facts": "Synthetic integration test; no client data."})
        assert response.status_code == 201, response.text
        result = response.json()
        returned = {s["source_id"] for s in result["sources"]}
        assert returned and returned <= {str(i) for i in chunk_ids}
        assert result["research_result"]["status"] == "abstain"  # no fake sufficient assessor
        assert result["history"]["answer"] is None
        for sid in returned:
            detail = api.get(f"/api/v1/sources/{sid}").json()
            assert detail["source_page"] == fixture["pdf_page"]
            assert detail["url"] == fixture["source_url"]
            assert detail["content"] in [c["content"] for c in chunks]
            assert detail["khoan"] is None
        saved = api.get(f"/api/v1/matters/{mid}/history").json()
        assert saved[0]["id"] == result["history"]["id"]
        print(json.dumps({"status": "pass", "run_at": datetime.now(timezone.utc).isoformat(),
                          "source": fixture["doc_code"], "pdf_sha256": fixture["pdf_sha256"],
                          "pdf_page": fixture["pdf_page"], "parsed_articles": fixture["expected_articles"],
                          "stored_chunks": len(chunk_ids), "matched_sources": len(returned),
                          "matter_id": mid, "history_id": saved[0]["id"],
                          "source_page_verified": True, "anonymous_api_status": 401,
                          "research_status": result["research_result"]["status"],
                          "legal_review_status": "pending_expert_review"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
