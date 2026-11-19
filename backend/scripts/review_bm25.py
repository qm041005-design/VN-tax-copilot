"""Export registry IDs/metadata and compare lexical BM25 with explicit legal references."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory

from sqlalchemy import select, text

from app.core.database import SessionLocal
from app.models import LegalDocument, LegalDocumentTaxScope
from app.services import source_service
from backend.scripts.profile_bm25 import profile


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def model_metadata(model):
    values = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        values[column.name] = value.isoformat() if isinstance(value, (date, datetime)) else value
    return values


def export_corpus(db):
    documents = [model_metadata(doc) for doc in db.scalars(select(LegalDocument).order_by(LegalDocument.id))]
    scopes = {}
    for doc_id, tax_type in db.execute(select(LegalDocumentTaxScope.doc_id, LegalDocumentTaxScope.tax_type)
                                     .order_by(LegalDocumentTaxScope.doc_id, LegalDocumentTaxScope.tax_type)):
        scopes.setdefault(doc_id, []).append(tax_type)
    passages = []
    for chunk in source_service.load_search_candidates(db):
        passages.append({"passage_id": str(chunk.id), "document_id": str(chunk.doc_id),
                         "tax_types": scopes.get(chunk.doc_id, []),
                         **source_service.to_detail(chunk).model_dump(mode="json"),
                         "chunk_metadata": model_metadata(chunk)})
    data = {"documents": documents, "tax_scopes": {str(key): value for key, value in scopes.items()},
            "passages": passages}
    return {"snapshot_sha256": digest(data), **data,
            "document_count": len(documents), "passage_count": len(passages),
            "coverage": {field: sum(row.get(field) is not None and row.get(field) != "" for row in passages)
                         for field in ("url", "source_page", "effective_date", "expiry_date", "version")},
            "tax_labeled_passages": sum(bool(row["tax_types"]) for row in passages)}


def compare_reports(baseline, current):
    rows = []
    for before, after in zip(baseline["cases"], current["cases"], strict=True):
        if before["case_id"] != after["case_id"] or before["candidate_sha256"] != after["candidate_sha256"]:
            raise ValueError("Không thể so sánh hai tập ứng viên khác nhau.")
        old, new = before["recall_at_10"], after["recall_at_10"]
        rows.append({"case_id": after["case_id"], "question": after["question"],
                     "candidate_count": after["candidate_count"], "baseline_recall_at_10": old,
                     "current_recall_at_10": new, "recall_delta": new - old if old is not None else None,
                     "baseline_ids": before["retrieved_passage_ids"],
                     "current_ids": after["retrieved_passage_ids"]})
    labeled = [row for row in rows if row["recall_delta"] is not None]
    samples = [sample for case in current["cases"] for sample in case["timing_samples"]]
    total_ms = sum(sample["total_ms"] for sample in samples)
    return {"scope": "development_comparison", "acceptance_status": "NOT_EVALUATED",
            "labeled_case_count": len(labeled), "unlabeled_case_count": len(rows) - len(labeled),
            "baseline_macro_recall_at_10": mean(row["baseline_recall_at_10"] for row in labeled) if labeled else None,
            "current_macro_recall_at_10": mean(row["current_recall_at_10"] for row in labeled) if labeled else None,
            "improved_case_ids": [row["case_id"] for row in labeled if row["recall_delta"] > 0],
            "regressed_case_ids": [row["case_id"] for row in labeled if row["recall_delta"] < 0],
            "current_index_build_fraction": sum(sample["index_build_ms"] for sample in samples) / total_ms
                                            if total_ms else None,
            "missing_evidence_by_reason": dict(Counter(evidence["reason"] for case in current["cases"]
                for evidence in case["evidence_results"] if not evidence["found"])), "cases": rows}


def review(db, benchmark, repeats=10):
    corpus = export_corpus(db)
    baseline = profile(db, benchmark, repeats, ranking_mode="bm25")
    current = profile(db, benchmark, repeats, ranking_mode="legal_references")
    comparison = {"snapshot_sha256": corpus["snapshot_sha256"], **compare_reports(baseline, current)}
    retrieval = [{"case_id": case["case_id"], "retrieved_passage_ids": case["retrieved_passage_ids"]}
                 for case in current["cases"]]
    return {"corpus": corpus, "benchmark": benchmark, "baseline": baseline, "current": current,
            "comparison": comparison, "retrieval": retrieval}


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def markdown(bundle):
    corpus, comparison, current = bundle["corpus"], bundle["comparison"], bundle["current"]
    lines = ["# SCRUM-31 — báo cáo phát triển BM25", "", f"Snapshot: `{corpus['snapshot_sha256']}`", "",
             f"Corpus: {corpus['document_count']} văn bản, {corpus['passage_count']} đoạn.",
             f"Có {comparison['labeled_case_count']} câu có nhãn và {comparison['unlabeled_case_count']} câu chưa có nhãn.",
             "Trạng thái nghiệm thu là NOT_EVALUATED. Báo cáo giữ nguyên nhãn đầu vào.", "",
             "| Metadata | Số đoạn có giá trị |", "|---|---:|"]
    lines += [f"| {field} | {count} |" for field, count in corpus["coverage"].items()]
    lines += ["", "Ngày hết hiệu lực null có thể biểu thị khoảng mở; không tự kết luận là lỗi.", "",
              "| Case | Recall BM25 | Recall có tham chiếu | ID kết quả hiện tại |", "|---|---:|---:|---|"]
    lines += [f"| {cell(row['case_id'])} | {row['baseline_recall_at_10']} | {row['current_recall_at_10']} | "
              f"{cell(', '.join(row['current_ids']))} |" for row in comparison["cases"]]
    lines += ["", "| Công đoạn | Trung vị (ms) | P95 (ms) |", "|---|---:|---:|"]
    lines += [f"| {stage} | {stats['median_ms']:.3f} | {stats['p95_ms']:.3f} |"
              for stage, stats in current["summary"].items()]
    fraction = comparison["current_index_build_fraction"]
    if fraction is not None:
        lines += ["", f"Xây chỉ mục chiếm {fraction:.1%} tổng thời gian các mẫu đo hiện tại."]
    lines += ["", "Đo trong tiến trình, chưa gồm HTTP hoặc ghi JSON. BM25 thuần chạy trước nên so sánh thời gian",
              "có thể chịu ảnh hưởng warm cache; cần chạy lại trên corpus tích hợp và tải sử dụng đại diện.", "",
              "## Phân tích với QA", "",
              "Dùng evidence.csv để xem lý do thiếu căn cứ và thứ hạng trước/sau. Đan điền kết luận vào",
              "qa_notes sau khi đối chiếu source_id, passage_id, nội dung, Điều/Khoản/Điểm, trang và kỳ thuế.",
              "corpus.json giữ toàn văn và ID thật, không nhập lại hay đánh lại ID khi trao đổi benchmark.", "",
              "## Đề xuất cập nhật chỉ mục", "",
              "Giữ lọc sắc thuế và thời gian trước khi tính IDF. Khi chi phí xây đáng kể ở quy mô thực tế,",
              "cache chỉ mục theo phiên bản corpus cùng bộ lọc đã chuẩn hóa. Sau transaction nhập/sửa metadata",
              "commit thành công, tăng phiên bản dữ liệu, xây snapshot mới rồi đổi tham chiếu một lần.",
              "Một request dùng trọn một snapshot; request tiếp theo đọc phiên bản mới. Nếu nhiều worker,",
              "phiên bản và tín hiệu invalidation phải dùng chung. Không dùng TTL làm cách duy nhất phát hiện cập nhật.",
              "Đo lại độ trễ, chi phí xây, bộ nhớ và Recall trên cùng snapshot trước khi triển khai cache.", ""]
    return "\n".join(lines)


def write_bundle(bundle, output_dir):
    if output_dir.exists():
        raise ValueError("Thư mục đầu ra đã tồn tại; chọn tên mới để giữ báo cáo trước.")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".bm25-review-", dir=output_dir.parent) as temporary:
        folder = Path(temporary)
        for name, value in bundle.items():
            (folder / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
                                                + "\n", encoding="utf-8")
        (folder / "review.md").write_text(markdown(bundle), encoding="utf-8")
        old = {case["case_id"]: case for case in bundle["baseline"]["cases"]}
        with (folder / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as output:
            fields = ("case_id", "question", "review_status", "evidence_id", "source_id", "description",
                      "acceptable_passage_ids", "baseline_found", "baseline_rank", "baseline_reason",
                      "current_found", "current_rank", "reason", "qa_notes")
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for case in bundle["current"]["cases"]:
                before = {row["evidence_id"]: row for row in old[case["case_id"]]["evidence_results"]}
                for evidence in case["evidence_results"]:
                    previous = before[evidence["evidence_id"]]
                    row = {"case_id": case["case_id"], "question": case["question"],
                        "review_status": case.get("review_status"),
                        "source_id": evidence.get("source_id"), "description": evidence.get("description"),
                        "evidence_id": evidence["evidence_id"],
                        "acceptable_passage_ids": ";".join(evidence["acceptable_passage_ids"]),
                        "baseline_found": previous["found"], "baseline_rank": previous["best_matching_rank"],
                        "baseline_reason": previous["reason"],
                        "current_found": evidence["found"], "current_rank": evidence["best_matching_rank"],
                        "reason": evidence["reason"]}
                    writer.writerow({key: "'" + value if isinstance(value, str)
                                     and value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value
                                     for key, value in row.items()})
        folder.rename(output_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--benchmark", type=Path)
    inputs.add_argument("--query", action="append")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output_dir.exists():
            raise ValueError("Thư mục đầu ra đã tồn tại; chọn tên mới.")
        benchmark = json.loads(args.benchmark.read_text(encoding="utf-8-sig")) if args.benchmark else {
            "cases": [{"case_id": f"QUERY-{number:03d}", "question": question, "answerability": "answerable"}
                      for number, question in enumerate(args.query, start=1)]}
        with SessionLocal.begin() as db:
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            bundle = review(db, benchmark, args.repeats)
        bundle["comparison"]["run_at"] = datetime.now(timezone.utc).isoformat()
        bundle["comparison"]["benchmark_sha256"] = digest(benchmark)
        write_bundle(bundle, args.output_dir)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps({"output_dir": str(args.output_dir), "snapshot_sha256": bundle["corpus"]["snapshot_sha256"],
                      "documents": bundle["corpus"]["document_count"], "passages": bundle["corpus"]["passage_count"],
                      "labeled_cases": bundle["comparison"]["labeled_case_count"],
                      "acceptance_status": "NOT_EVALUATED"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
