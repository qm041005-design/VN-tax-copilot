"""Run SCRUM-17 scenarios on an isolated backend, with no paid AI calls.

Usage: python -m evaluation.run_week3_integration --backend-root PATH --output PATH
Install the selected backend's requirements plus backend/requirements.txt here.
The backend is imported only after replacing DATABASE_URL with a fresh SQLite
file; this runner accepts no existing database URL and never drops user tables.
"""
import argparse
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch

from ai_engine.synthesis.backend_adapter import build_backend_messages
from backend.app.services.export_service import export_backend_research_docx


def revision(root):
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "-C", str(root), "diff", "HEAD", "--name-only"], text=True).strip())
    return {"sha": sha, "tracked_changes": dirty}


def run(backend_root, dataset_path):
    root = Path(__file__).resolve().parents[1]
    backend_root = Path(backend_root).resolve()
    if not (backend_root / "backend/app/main.py").is_file():
        raise ValueError("Select the integrated backend checkout")
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if len(dataset["cases"]) != 10 or len({c["case_id"] for c in dataset["cases"]}) != 10:
        raise ValueError("Expected exactly ten distinct week-3 cases")
    report = {"suite_id": dataset["suite_id"], "run_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
              "executor": "Đặng Minh Quân (Codex hỗ trợ)", "po_revision": revision(root),
              "backend_revision": revision(backend_root),
              "dataset_sha256": hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest(),
              "scope": "Technical API/adapter checks on fresh SQLite; not legal acceptance or live UI",
              "uses_real_legal_evidence": False, "paid_provider_calls": 0,
              "database": "new temporary SQLite; no demo/production database", "cases": []}
    report["po_file_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("ai_engine/synthesis/backend_adapter.py", "ai_engine/synthesis/prompt_templates.py",
                     "backend/app/services/export_service.py", "evaluation/run_week3_integration.py")}
    with tempfile.TemporaryDirectory(prefix="scrum17-") as tmp:
        os.environ.update(DATABASE_URL="sqlite:///" + (Path(tmp) / "week3.db").as_posix(),
                          APP_ENV="dev", AUTH_TOKENS="week3-local-test-token:quan:week3-test",
                          CORS_ORIGINS="http://localhost:3000")
        sys.path.insert(0, str(backend_root))
        sys.path.insert(0, str(backend_root / "backend"))
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import SessionLocal, engine
        from app.models import LegalDocument, LegalChunk
        from ai_engine.guardrails import EvidenceAssessment
        module = importlib.import_module("app.api.v1.research")
        headers = {"Authorization": "Bearer week3-local-test-token"}
        try:
            with TestClient(app) as client:
                for case in dataset["cases"]:
                    case_id = case["case_id"]
                    created = client.post("/api/v1/matters", headers=headers,
                                          json={"title": case_id + " isolated test", "client_name": "Technical fixture"})
                    created.raise_for_status()
                    mid = created.json()["id"]
                    request = dict(case["request_template"], matter_id=mid)
                    generator = Mock(side_effect=AssertionError("Generation must not run"))
                    assessor = Mock(return_value=[])
                    context = nullcontext()
                    if case_id == "W3-009":
                        context = patch.object(module.source_service, "search", return_value=[])
                    elif case_id == "W3-010":
                        with SessionLocal() as db:
                            doc = LegalDocument(doc_code="W3-TECHNICAL-UNVERIFIED", title="NOT A LEGAL SOURCE",
                                                doc_type="UNKNOWN", hierarchy_level=5, effective_date=None,
                                                source_url="https://example.org/technical-fixture", version="fixture-v1")
                            db.add(doc)
                            db.flush()
                            row = LegalChunk(doc_id=doc.id, article_number="1", clause_number="0",
                                             citation_path="Technical fixture only", source_page=1,
                                             hierarchy_level=5, content="Technical placeholder, not a tax rule.")
                            db.add(row)
                            db.commit()
                            _ = row.document.doc_code, row.content, row.id
                        context = patch.object(module.source_service, "search", return_value=[(row, 1.0)])
                        assessor.side_effect = lambda safe: [EvidenceAssessment(p["passage_id"], False) for p in safe.passages]
                    # Only isolated refusal cases use a test assessor; never sufficient=True.
                    if case_id in ("W3-009", "W3-010"):
                        app.dependency_overrides[module.research_callbacks] = lambda: (assessor, generator)
                    try:
                        with context:
                            response = client.post("/api/v1/research", headers=headers, json=request)
                        response.raise_for_status()
                        body = response.json()
                        history = client.get(f"/api/v1/matters/{mid}/history", headers=headers)
                        history.raise_for_status()
                        details = []
                        for source in body["sources"]:
                            detail = client.get("/api/v1/sources/" + source["source_id"], headers=headers)
                            detail.raise_for_status()
                            details.append(detail.json())
                        messages = build_backend_messages(request, details,
                                                          allowed_source_ids=[s["source_id"] for s in body["sources"]])
                        blob = export_backend_research_docx(body, details, matter_id=mid)
                        actual = body["research_result"]
                        questions = " ".join(actual["clarification_questions"]).casefold()
                        checks = {"six_sections": set(actual["sections"]) == {"issue", "facts", "authority", "analysis", "limitations", "next_steps"},
                                  "matter_preserved": body["history"]["matter_id"] == mid,
                                  "question_preserved": body["history"]["question"] == request["question"],
                                  "history_saved": any(h["id"] == body["history"]["id"] for h in history.json()),
                                  "no_auto_approval": body["history"]["review_status"] == "draft",
                                  "no_answer_without_assessment": body["history"]["answer"] is None,
                                  "generator_not_called": not generator.called,
                                  "no_legal_claims_on_refusal": not any(actual["sections"].values()),
                                  "prompt_uses_fulltext": all(p["text"] == d["content"] for p, d in zip(json.loads(messages[1]["content"])["passages"], details)),
                                  "docx_created": blob.startswith(b"PK")}
                        blockers = []
                        if case["scenario"] == "verified_evidence":
                            blockers = ["No expert-reviewed evidence with real registry IDs/PDF pages bound to this case.",
                                        "No real evidence assessor/generator configured; draft cannot be tested."]
                        else:
                            checks["expected_status"] = actual["status"] == case["expected"]["synthesis_status"]
                        if case_id == "W3-007":
                            checks["asks_goods_or_services"] = any(w in questions for w in ("hàng hóa", "dịch vụ", "mặt hàng"))
                            checks["asks_tax_method"] = "phương pháp" in questions
                        if case_id == "W3-008":
                            checks["asks_presence_days"] = "có mặt" in questions
                            checks["asks_residence"] = any(w in questions for w in ("nơi ở", "thuê nhà", "cư trú"))
                        if case_id == "W3-010":
                            checks["insufficient_assessor_exercised"] = assessor.called
                        status = "fail" if not all(checks.values()) else "blocked" if blockers else "pass"
                        report["cases"].append({"case_id": case_id, "scenario": case["scenario"],
                                                "execution": {"status": status, "blockers": blockers,
                                                              "checks": checks, "actual_result": body,
                                                              "history_reopened": history.json(),
                                                              "source_details": details,
                                                              "docx_sha256": hashlib.sha256(blob).hexdigest()},
                                                "limitations": ["Fixture-only technical run; no legal conclusions validated."]})
                    finally:
                        app.dependency_overrides.clear()
        finally:
            engine.dispose()
    report["summary"] = dict(Counter(c["execution"]["status"] for c in report["cases"]))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", required=True)
    parser.add_argument("--dataset", default=str(Path(__file__).parent / "datasets/week3_integration_cases.json"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.backend_root, args.dataset)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))
    # Blocked prerequisites and observed behavior failures must remain visible in CI.
    return 1 if report["summary"].get("fail") else 2 if report["summary"].get("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
