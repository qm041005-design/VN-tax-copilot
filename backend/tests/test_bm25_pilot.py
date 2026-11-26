"""The checked-in evidence labels must resolve after rebuilding the pilot."""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.services.source_service import load_search_candidates, to_detail
from backend.scripts.export_bm25_retrieval import retrieve_benchmark
from evaluation.datasets.legal_pilot.build_snapshot import build_snapshot

PILOT = Path(__file__).resolve().parents[2] / "evaluation/datasets/legal_pilot"


def test_pilot_snapshot_reproduces_citations_and_ranked_ids(tmp_path):
    folder = PILOT
    benchmark = json.loads((folder / "benchmark.json").read_text(encoding="utf-8"))
    expected = json.loads((folder / "retrieval.json").read_text(encoding="utf-8"))
    rebuilt = tmp_path / "rebuilt.sqlite3"
    build_snapshot(rebuilt)
    snapshots = []
    for path in (folder / "registry.sqlite3", rebuilt):
        assert path.is_file()
        engine = create_engine(URL.create("sqlite", database=str(path)))
        try:
            with Session(engine) as db:
                snapshots.append({
                    str(chunk.id): to_detail(chunk).model_dump()
                    for chunk in load_search_candidates(db)
                })
                assert retrieve_benchmark(db, benchmark) == expected
        finally:
            engine.dispose()
    assert snapshots[0] == snapshots[1]
    for case in benchmark["cases"]:
        for evidence in case["required_evidence"]:
            assert evidence["acceptable_passage_ids"]
            assert set(evidence["acceptable_passage_ids"]) <= snapshots[0].keys()


def test_snapshot_search_and_source_metadata_match_qa_exports(monkeypatch):
    benchmark = json.loads((PILOT / "benchmark.json").read_text(encoding="utf-8"))
    sources = json.loads((PILOT / "sources.json").read_text(encoding="utf-8"))
    with (PILOT / "passages.csv").open(encoding="utf-8-sig") as passages:
        rows = list(csv.DictReader(passages))
    engine = create_engine(URL.create("sqlite", database=str(PILOT / "registry.sqlite3")))

    def snapshot_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, snapshot_db)
    client = TestClient(app, headers={"Authorization": "Bearer test-token-alice-local"})
    try:
        docs = {s["document"]["doc_code"]: s["document"] for s in sources}
        for row in rows:
            response = client.get(f"/api/v1/sources/{row['passage_id']}")
            assert response.status_code == 200
            hit = response.json()
            doc = docs[row["legal_identifier"]]
            assert hit["source_id"] == row["passage_id"]
            assert hit["legal_identifier"] == row["legal_identifier"]
            assert (hit["dieu"], hit["khoan"], hit["diem"]) == (
                row["article"], row["clause"] or None, row["point"] or None)
            assert (hit["url"], hit["source_page"]) == (row["source_url"], int(row["pdf_page"]))
            assert (hit["citation_path"], hit["content"]) == (row["citation_path"], row["content"])
            assert (hit["version"], hit["status"]) == (doc["version"], "CHUA_XAC_DINH")
            assert hit["effective_date"][:10] == doc["effective_date"]
            assert hit["expiry_date"] == doc["expiry_date"]

        full_export = PILOT.parents[1] / "reports/scrum41/retrieval_unfiltered.json"
        for filtered, path in ((True, PILOT / "retrieval.json"), (False, full_export)):
            exported = json.loads(path.read_text(encoding="utf-8"))
            for case, result in zip(benchmark["cases"], exported, strict=True):
                assert case["case_id"] == result["case_id"]
                params = {"q": case["question"]}
                if filtered:
                    params["tax_type"] = case["category"]
                response = client.get("/api/v1/sources/search", params=params)
                assert response.status_code == 200
                ids = [hit["source_id"] for hit in response.json()]
                assert ids == result["retrieved_passage_ids"]
                groups = [g["acceptable_passage_ids"] for g in case["required_evidence"]]
                assert any(ids[0] in group for group in groups)
                assert all(set(ids).intersection(group) for group in groups)

        for source in sources:
            code = source["document"]["doc_code"]
            tax = source["tax_type"]
            expected = {row["passage_id"] for row in rows if row["tax_type"] == tax}
            start = date.fromisoformat(source["document"]["effective_date"])
            previous = start - timedelta(days=1)
            quarter = (start.month - 1) // 3 + 1
            for filters, included in [
                ({"as_of": previous.isoformat()}, False),
                ({"as_of": start.isoformat()}, True),
                ({"tax_period": str(start.year)}, True),
                ({"tax_period": f"{start.year}-Q{quarter}"}, True),
                ({"tax_period": previous.strftime("%Y-%m"), "as_of": start.isoformat()}, False),
                ({"tax_period": start.strftime("%Y-%m"), "as_of": previous.isoformat()}, True),
            ]:
                params = {"q": code, "tax_type": tax, "limit": 50, **filters}
                response = client.get("/api/v1/sources/search", params=params)
                assert response.status_code == 200
                assert {hit["source_id"] for hit in response.json()} == (expected if included else set())
    finally:
        client.close()
        engine.dispose()
