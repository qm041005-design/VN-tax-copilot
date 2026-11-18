
import argparse
import json
from jsonschema import Draft202012Validator
import sys
from collections import Counter, defaultdict
from pathlib import Path

def load_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def average(values):
    return sum(values) / len(values) if values else None


def validate_inputs(benchmark, retrieval_results):
    if not isinstance(benchmark, dict):
        raise ValueError("Benchmark phai la JSON object.")

    cases = benchmark.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Benchmark phai co danh sach cases.")

    if not isinstance(retrieval_results, list):
        raise ValueError("Retrieval results phai la JSON array.")

    case_ids = set()
    answerable_ids = set()
    categories = Counter()
    special_tags = Counter()
    answerability_counts = Counter()
    review_issues = []
    source_issues = []

    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Moi case phai la JSON object.")

        case_id = case["case_id"]

        if not isinstance(case_id, str) or not case_id:
            raise ValueError("case_id khong hop le.")

        if case_id in case_ids:
            raise ValueError(f"Trung case_id: {case_id}")

        case_ids.add(case_id)

        answerability = case["answerability"]
        category = case["category"]

        if answerability not in (
            "answerable", "unanswerable", "ambiguous"
        ):
            raise ValueError(
                f"{case_id}: answerability khong hop le."
            )

        if category not in (
            "VAT", "CIT", "PIT", "TAX_ADMIN", "E_INVOICE"
        ):
            raise ValueError(f"{case_id}: category khong hop le.")

        answerability_counts[answerability] += 1


        reviewers = case.get("reviewers", [])
        reviewer_ids = []

        if not isinstance(reviewers, list):
            review_issues.append(f"{case_id}: reviewers khong hop le.")
        else:
            for reviewer in reviewers:
                if not isinstance(reviewer, dict):
                    review_issues.append(
                        f"{case_id}: reviewer khong hop le."
                    )
                    continue

                reviewer_id = reviewer.get("reviewer_id")
                decision = reviewer.get("decision")

                if not isinstance(reviewer_id, str) or not reviewer_id.strip():
                    review_issues.append(
                        f"{case_id}: reviewer_id thieu."
                    )
                else:
                    reviewer_ids.append(reviewer_id.strip())

                if decision != "approved":
                    review_issues.append(
                        f"{case_id}: reviewer chua approved."
                    )

            if len(reviewers) != 2:
                review_issues.append(
                    f"{case_id}: can dung 2 reviewers."
                )

            if len(reviewer_ids) != 2 or len(set(reviewer_ids)) != 2:
                review_issues.append(
                    f"{case_id}: reviewers phai doc lap."
                )

        if case.get("review_status") != "approved":
            review_issues.append(
                f"{case_id}: review_status chua approved."
            )

        if answerability != "answerable":
            continue

        tags = case.get("tags", [])

        if isinstance(tags, list):
            if "historical" in tags or "amendment" in tags:
                special_tags["history_amendment"] += 1

            if "conflicting_sources" in tags:
                special_tags["conflicting_sources"] += 1


        answerable_ids.add(case_id)
        categories[category] += 1

        evidence_list = case["required_evidence"]

        if not isinstance(evidence_list, list) or not evidence_list:
            raise ValueError(
                f"{case_id}: required_evidence phai co du lieu."
            )

        evidence_ids = set()

        for evidence in evidence_list:
            if not isinstance(evidence, dict):
                raise ValueError(
                    f"{case_id}: evidence khong hop le."
                )

            evidence_id = evidence["evidence_id"]

            if evidence_id in evidence_ids:
                raise ValueError(
                    f"{case_id}: Trung evidence_id {evidence_id}"
                )

            evidence_ids.add(evidence_id)

            acceptable = evidence.get("acceptable_passage_ids")

            if (
                not isinstance(acceptable, list)
                or not acceptable
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in acceptable
                )
            ):
                raise ValueError(
                    f"{case_id}: {evidence_id} thieu "
                    "acceptable_passage_ids hop le."
                )

            source_id = evidence.get("source_id")

            if not isinstance(source_id, str) or not source_id.strip():
                source_issues.append(
                    f"{case_id}: {evidence_id} thieu source_id."
                )

    results_by_id = {}

    for result in retrieval_results:
        if not isinstance(result, dict):
            raise ValueError("Retrieval result phai la object.")

        case_id = result["case_id"]

        if case_id in results_by_id:
            raise ValueError(
                f"Trung retrieval result: {case_id}"
            )

        passages = result["retrieved_passage_ids"]

        if (
            not isinstance(passages, list)
            or not all(
                isinstance(passage_id, str) and passage_id.strip()
                for passage_id in passages
            )
        ):
            raise ValueError(
                f"{case_id}: retrieved_passage_ids khong hop le."
            )

        results_by_id[case_id] = passages

    missing = answerable_ids - results_by_id.keys()

    if missing:
        raise ValueError(
            "Thieu retrieval results: "
            + ", ".join(sorted(missing))
        )

    benchmark_issues = []

    if len(cases) != 250:
        benchmark_issues.append(
            f"Can 250 cases, hien co {len(cases)}."
        )

    if answerability_counts["answerable"] != 200:
        benchmark_issues.append(
            "Can dung 200 answerable cases."
        )

    trap_count = (
        answerability_counts["unanswerable"]
        + answerability_counts["ambiguous"]
    )

    if trap_count != 50:
        benchmark_issues.append(
            "Can dung 50 trap cases."
        )

    for category in ("VAT", "CIT", "PIT"):
        if categories[category] < 60:
            benchmark_issues.append(
                f"{category}: can it nhat 60 answerable cases."
            )
        admin_invoice_count = (
        categories["TAX_ADMIN"] + categories["E_INVOICE"]
    )

    if admin_invoice_count < 20:
        benchmark_issues.append(
            "Can it nhat 20 answerable cases TAX_ADMIN/E_INVOICE."
        )

    if special_tags["history_amendment"] < 40:
        benchmark_issues.append(
            "Can it nhat 40 cases historical/amendment."
        )

    if special_tags["conflicting_sources"] < 30:
        benchmark_issues.append(
            "Can it nhat 30 cases conflicting_sources."
        )

    return {
        "results_by_id": results_by_id,
        "answerability_counts": dict(answerability_counts),
        "category_counts": dict(categories),
        "benchmark_issues": benchmark_issues,
        "review_issues": review_issues,
        "source_issues": source_issues,
    }


def calculate_recall_at_10(required_evidence, retrieved_passages):
    top_10 = set(retrieved_passages[:10])
    matched = 0
    evidence_results = []

    for evidence in required_evidence:
        acceptable = set(evidence["acceptable_passage_ids"])
        found = bool(top_10.intersection(acceptable))

        if found:
            matched += 1

        evidence_results.append({
            "evidence_id": evidence["evidence_id"],
            "found": found,
            "source_id": evidence.get("source_id")
        })

    return matched / len(required_evidence), evidence_results


def evaluate(benchmark, retrieval_results):
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "benchmark.schema.json"
    )

    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)

    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(benchmark),
        key=lambda error: str(error.json_path)
    )

    if schema_errors:
        return {
            "benchmark_valid": False,
            "at03_status": "NOT_EVALUATED",
            "validation_issues": [
                f"{error.json_path}: {error.message}"
                for error in schema_errors
            ],
        }

    validation = validate_inputs(benchmark, retrieval_results)

    results_by_id = validation["results_by_id"]

    case_results = []
    category_scores = defaultdict(list)
    source_counts = defaultdict(
        lambda: {"matched": 0, "required": 0}
    )

    for case in benchmark["cases"]:
        if case["answerability"] != "answerable":
            continue

        case_id = case["case_id"]
        category = case["category"]

        recall, evidence_results = calculate_recall_at_10(
            case["required_evidence"],
            results_by_id[case_id]
        )

        category_scores[category].append(recall)

        for evidence in evidence_results:
            source_id = evidence["source_id"]

            # UNKNOWN chi dung de chan doan du lieu thieu.
            # Du lieu thieu source_id khong duoc bao PASS.
            if not isinstance(source_id, str) or not source_id.strip():
                source_id = "UNKNOWN"

            source_counts[source_id]["required"] += 1

            if evidence["found"]:
                source_counts[source_id]["matched"] += 1

        case_results.append({
            "case_id": case_id,
            "category": category,
            "recall_at_10": recall,
            "required_count": len(evidence_results),
            "matched_count": sum(
                item["found"] for item in evidence_results
            ),
            "evidence_results": evidence_results
        })

        print(f"{case_id}: Recall@10 = {recall:.2%}")

    if not case_results:
        raise ValueError("Khong co cau hoi answerable.")

    macro_recall = average([
        item["recall_at_10"] for item in case_results
    ])

    category_report = {}

    for category, scores in category_scores.items():
        category_report[category] = {
            "case_count": len(scores),
            "macro_recall_at_10": average(scores)
        }

    source_report = {}

    for source_id, counts in source_counts.items():
        source_report[source_id] = {
            "matched_evidence": counts["matched"],
            "required_evidence": counts["required"],
            "evidence_recall_at_10": (
                counts["matched"] / counts["required"]
            )
        }

    all_issues = (
        validation["benchmark_issues"]
        + validation["review_issues"]
        + validation["source_issues"]
    )

    benchmark_valid = not all_issues

    if not benchmark_valid:
        at03_status = "NOT_EVALUATED"
    elif macro_recall >= 0.90:
        at03_status = "PASS"
    else:
        at03_status = "FAIL"

    report = {
        "metric": "Recall@10",
        "requirement_ids": ["EVAL 05", "AT 03"],
        "answerable_case_count": len(case_results),
        "answerability_counts": validation["answerability_counts"],
        "category_counts": validation["category_counts"],
        "macro_recall_at_10": macro_recall,
        "at03_threshold": 0.90,
        "at03_status": at03_status,
        "benchmark_valid": benchmark_valid,
        "validation_issues": all_issues,
        "cases": case_results,
        "by_category": category_report,
        "by_source": source_report
    }

    print("\n===== KET QUA TONG HOP =====")
    print(f"So cau hoi answerable: {len(case_results)}")
    print(f"Macro Recall@10: {macro_recall:.2%}")
    print(f"Benchmark hop le: {benchmark_valid}")
    print(f"AT03: {at03_status}")

    if all_issues:
        print("\n===== VAN DE CAN KHAC PHUC =====")
        for issue in all_issues[:20]:
            print(f"- {issue}")

        if len(all_issues) > 20:
            print(f"... va {len(all_issues) - 20} van de khac.")

    print("\n===== THEO NHOM THUE =====")

    for category, data in category_report.items():
        print(
            f"{category}: "
            f"{data['macro_recall_at_10']:.2%} "
            f"({data['case_count']} cau)"
        )

    print("\n===== THEO NGUON =====")

    for source_id, data in source_report.items():
        print(
            f"{source_id}: "
            f"{data['evidence_recall_at_10']:.2%} "
            f"({data['matched_evidence']}/"
            f"{data['required_evidence']})"
        )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="VN Tax Copilot Recall@10 Evaluation"
    )

    parser.add_argument(
        "--benchmark",
        required=True,
        help="Duong dan benchmark JSON"
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--retrieval",
        help="Duong dan retrieval results JSON"
    )

    group.add_argument(
        "--passages",
        help="Duong dan passages JSON de chay BM25"
    )
    parser.add_argument(
        "--output",
        default="evaluation/metrics/recall_report.json",
        help="Duong dan file bao cao JSON"
    )

    args = parser.parse_args()

    try:
        benchmark = load_json(args.benchmark)

        if args.passages:
            from evaluation.metrics.bm25_adapter import run_bm25_retrieval

            passages = load_json(args.passages)
            if not isinstance(passages, list):
                raise ValueError("Passages phai la JSON array.")
            retrieval_results = run_bm25_retrieval(benchmark, passages)
        else:
            retrieval_results = load_json(args.retrieval)

        report = evaluate(benchmark, retrieval_results)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(f"\nDa luu bao cao: {output_path}")

    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
