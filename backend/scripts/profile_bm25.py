"""Measure the backend BM25 stages and diagnose missing evidence on one DB snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import ceil
from pathlib import Path
from statistics import median
from tempfile import mkstemp
from time import perf_counter

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import LegalChunk, LegalDocument
from app.services import source_service
from ai_engine.retrieval import bm25
from backend.scripts.export_bm25_retrieval import benchmark_search_options


RANKING_MODES = ("legal_references", "bm25")


def summarize(samples):
    ordered = sorted(samples)
    return {"min_ms": ordered[0], "median_ms": median(ordered),
            "p95_ms": ordered[ceil(0.95 * len(ordered)) - 1], "max_ms": ordered[-1]}


def diagnose_evidence(evidence, top_ids, candidate_ids, registry_ids, ranking):
    results = []
    evidence_ids = set()
    for item in evidence:
        evidence_id = item["evidence_id"]
        if not isinstance(evidence_id, str) or not evidence_id.strip() or evidence_id in evidence_ids:
            raise ValueError("evidence_id phải là chuỗi có nội dung, duy nhất trong mỗi case.")
        evidence_ids.add(evidence_id)
        acceptable = item["acceptable_passage_ids"]
        if (not isinstance(acceptable, list) or not acceptable
                or any(not isinstance(pid, str) or not pid.strip() for pid in acceptable)):
            raise ValueError("acceptable_passage_ids phải là danh sách ID chuỗi, có ít nhất một phần tử.")
        acceptable = set(acceptable)
        found = bool(acceptable.intersection(top_ids))
        eligible = acceptable.intersection(candidate_ids)
        ranks = [ranking[pid] for pid in acceptable if pid in ranking]
        reason = None
        if not found:
            if not acceptable.intersection(registry_ids):
                reason = "missing_from_registry"
            elif not eligible:
                reason = "excluded_by_filters"
            elif ranks:
                reason = "below_top10"
            else:
                reason = "no_token_overlap"
        results.append({"evidence_id": evidence_id, "source_id": item.get("source_id"),
                        "description": item.get("description"), "found": found,
                        "acceptable_passage_ids": sorted(acceptable),
                        "best_matching_rank": min(ranks) if ranks else None, "reason": reason})
    return results


def profile_case(db, case, registry_ids, repeats, ranking_mode="legal_references"):
    question = case["question"]
    if not isinstance(question, str) or not bm25.tokenize(question):
        raise ValueError(f"{case['case_id']}: câu hỏi phải là chuỗi có nội dung.")
    try:
        filters = benchmark_search_options(case)
    except ValueError as exc:
        raise ValueError(f"{case['case_id']}: {exc}") from exc
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        chunks = source_service.load_search_candidates(db, **filters)
        loaded = perf_counter()
        lookup = {str(chunk.id): chunk for chunk in chunks}
        retriever = source_service.build_retriever(chunks, use_legal_references=ranking_mode == "legal_references")
        built = perf_counter()
        hits = retriever.search(question, limit=10)
        ranked = perf_counter()
        samples.append({"db_ms": (loaded - start) * 1000, "index_build_ms": (built - loaded) * 1000,
                        "rank_ms": (ranked - built) * 1000, "total_ms": (ranked - start) * 1000})

    top_ids = [hit["passage_id"] for hit in hits]
    # Diagnostic ranking is outside the timed top-10 search.
    all_hits = retriever.search(question, limit=len(chunks))
    ranking = {hit["passage_id"]: rank for rank, hit in enumerate(all_hits, start=1)}
    required = case.get("required_evidence", [])
    if not isinstance(required, list):
        raise ValueError(f"{case['case_id']}: required_evidence phải là danh sách.")
    evidence = diagnose_evidence(required, set(top_ids), set(lookup),
                                 registry_ids, ranking)
    sources = [
        {"passage_id": hit["passage_id"], "score": hit["score"],
         **source_service.to_detail(lookup[hit["passage_id"]]).model_dump(mode="json")}
        for hit in hits
    ]
    fingerprint = hashlib.sha256()
    for chunk in chunks:
        fingerprint.update(json.dumps(source_service.to_detail(chunk).model_dump(mode="json"),
                                      ensure_ascii=False, sort_keys=True).encode("utf-8"))
        fingerprint.update(b"\n")
    return {"case_id": case["case_id"], "question": question, "category": case.get("category"),
            "review_status": case.get("review_status"), "reviewers": case.get("reviewers", []),
            "doc_type": case.get("doc_type"),
            "tax_period": case.get("tax_period"), "research_as_of": case.get("research_as_of"),
            "candidate_count": len(chunks), "candidate_sha256": fingerprint.hexdigest(),
            "retrieved_passage_ids": top_ids, "top10": sources, "timing_samples": samples,
            "timing_summary": {key: summarize([sample[key] for sample in samples]) for key in samples[0]},
            "evidence_results": evidence,
            "recall_at_10": sum(item["found"] for item in evidence) / len(evidence) if evidence else None}


def profile(db: Session, benchmark: dict, repeats: int = 5, *, ranking_mode="legal_references") -> dict:
    if not 1 <= repeats <= 100:
        raise ValueError("Số lần đo phải từ 1 đến 100.")
    if ranking_mode not in RANKING_MODES:
        raise ValueError("ranking_mode không hợp lệ.")
    cases = benchmark["cases"]
    if not isinstance(cases, list):
        raise ValueError("cases phải là danh sách.")
    ids = [case["case_id"] for case in cases]
    if any(not isinstance(case_id, str) or not case_id.strip() for case_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("case_id phải là chuỗi duy nhất, có nội dung.")
    registry_ids = {str(pid) for pid in db.scalars(select(LegalChunk.id))}
    results = []
    for case in cases:
        if case["answerability"] not in {"answerable", "unanswerable", "ambiguous"}:
            raise ValueError(f"{case['case_id']}: answerability không hợp lệ.")
        if case["answerability"] == "answerable":
            results.append(profile_case(db, case, registry_ids, repeats, ranking_mode))
    stages = ("db_ms", "index_build_ms", "rank_ms", "total_ms")
    summary = {key: summarize([sample[key] for case in results for sample in case["timing_samples"]])
               for key in stages} if results else {}
    code_files = {"source_service.py": Path(source_service.__file__), "bm25.py": Path(bm25.__file__),
                  "profile_bm25.py": Path(__file__)}
    return {"run_at": datetime.now(timezone.utc).isoformat(), "scope": "development_profiling",
            "ranking_mode": ranking_mode,
            "code_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in code_files.items()},
            "acceptance_status": "NOT_EVALUATED", "document_count": db.scalar(select(func.count(LegalDocument.id))),
            "passage_count": len(registry_ids), "repeats_per_case": repeats,
            "timing_scope": "DB read + mapping/tokenization/index construction + BM25 ranking. HTTP and JSON export excluded.",
            "summary": summary, "cases": results,
            "skipped_case_ids": [case["case_id"] for case in cases if case["answerability"] != "answerable"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--query", action="append", help="Có thể lặp lại để đo nhiều câu.")
    inputs.add_argument("--benchmark", type=Path, help="Benchmark theo cấu trúc của nhóm QA.")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--ranking-mode", choices=RANKING_MODES, default="legal_references")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.benchmark and args.output.resolve() == args.benchmark.resolve():
        parser.error("Chọn tệp đầu ra khác benchmark.")
    try:
        benchmark = json.loads(args.benchmark.read_text(encoding="utf-8-sig")) if args.benchmark else {
            "cases": [{"case_id": f"QUERY-{n:03d}", "question": question, "answerability": "answerable"}
                      for n, question in enumerate(args.query, start=1)]
        }
        with SessionLocal.begin() as db:
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            report = profile(db, benchmark, args.repeats, ranking_mode=args.ranking_mode)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd, name = mkstemp(dir=args.output.parent)
        temporary = Path(name)
        try:
            with open(fd, "w", encoding="utf-8") as output:
                json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
                output.write("\n")
            temporary.replace(args.output)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps({"documents": report["document_count"], "passages": report["passage_count"],
                      "summary": report["summary"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
