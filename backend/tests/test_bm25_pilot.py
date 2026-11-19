"""The checked-in evidence labels must resolve after rebuilding the pilot."""
import json
from pathlib import Path

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.services.source_service import load_search_candidates, to_detail
from backend.scripts.export_bm25_retrieval import retrieve_benchmark
from evaluation.datasets.legal_pilot.build_snapshot import build_snapshot


def test_pilot_snapshot_reproduces_citations_and_ranked_ids(tmp_path):
    folder = Path(__file__).resolve().parents[2] / "evaluation/datasets/legal_pilot"
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
