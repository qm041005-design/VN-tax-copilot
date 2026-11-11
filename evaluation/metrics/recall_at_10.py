
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

def load_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return json.load(file)

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

    for case in cases:
        case_id = case["case_id"]

        if case_id in case_ids:
            raise ValueError(f"Trung case_id: {case_id}")

        case_ids.add(case_id)

        if case["answerability"] != "answerable":
            continue

        answerable_ids.add(case_id)

        evidence_list = case["required_evidence"]

        if not evidence_list:
            raise ValueError(
                f"{case_id}: Khong co required_evidence."
            )

        evidence_ids = set()

        for evidence in evidence_list:
            evidence_id = evidence["evidence_id"]

            if evidence_id in evidence_ids:
                raise ValueError(
                    f"{case_id}: Trung evidence_id {evidence_id}"
                )

            evidence_ids.add(evidence_id)

            acceptable = evidence.get(
                "acceptable_passage_ids", []
            )

            if not acceptable:
                raise ValueError(
                    f"{case_id}: Evidence {evidence_id} "
                    "chua co acceptable_passage_ids."
                )

    results_by_id = {}

    for result in retrieval_results:
        case_id = result["case_id"]

        if case_id in results_by_id:
            raise ValueError(
                f"Trung retrieval result: {case_id}"
            )

        passages = result["retrieved_passage_ids"]

        if not isinstance(passages, list):
            raise ValueError(
                f"{case_id}: retrieved_passage_ids "
                "phai la danh sach."
            )

        if not all(
            isinstance(passage_id, str)
            for passage_id in passages
        ):
            raise ValueError(
                f"{case_id}: Passage ID phai la chuoi."
            )

        results_by_id[case_id] = passages

    missing = answerable_ids - results_by_id.keys()

    if missing:
        raise ValueError(
            "Thieu retrieval results: "
            + ", ".join(sorted(missing))
        )

    return results_by_id


def calculate_recall_at_10(
    required_evidence,
    retrieved_passages
):
    top_10 = set(retrieved_passages[:10])

    matched = 0
    evidence_results = []

    for evidence in required_evidence:
        acceptable = set(
            evidence["acceptable_passage_ids"]
        )

        found = bool(top_10.intersection(acceptable))

        if found:
            matched += 1

        evidence_results.append({
            "evidence_id": evidence["evidence_id"],
            "found": found,
            "source_id": evidence.get("source_id")
        })

    recall = matched / len(required_evidence)

    return recall, evidence_results


def average(values):
    if not values:
        return None

    return sum(values) / len(values)


def evaluate(benchmark, retrieval_results):
    results_by_id = validate_inputs(
        benchmark, retrieval_results
    )

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

            if source_id is None:
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
        raise ValueError(
            "Khong co cau hoi answerable."
        )

    macro_recall = average([
        item["recall_at_10"]
        for item in case_results
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

    answerable_count = len(case_results)

    if answerable_count != 200:
        at03_status = "NOT_EVALUATED"
    elif macro_recall >= 0.90:
        at03_status = "PASS"
    else:
        at03_status = "FAIL"

    report = {
        "metric": "Recall@10",
        "requirement_ids": ["EVAL 05", "AT 03"],
        "answerable_case_count": answerable_count,
        "macro_recall_at_10": macro_recall,
        "at03_threshold": 0.90,
        "at03_status": at03_status,
        "cases": case_results,
        "by_category": category_report,
        "by_source": source_report
    }

    print("\n===== KET QUA TONG HOP =====")
    print(f"So cau hoi: {answerable_count}")
    print(f"Macro Recall@10: {macro_recall:.2%}")
    print(f"AT03: {at03_status}")

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

    parser.add_argument(
        "--retrieval",
        required=True,
        help="Duong dan retrieval results JSON"
    )

    parser.add_argument(
        "--output",
        default="evaluation/metrics/recall_report.json",
        help="Duong dan luu bao cao JSON"
    )

    args = parser.parse_args()

    try:
        benchmark = load_json(args.benchmark)
        retrieval_results = load_json(args.retrieval)

        report = evaluate(
            benchmark, retrieval_results
        )

        output_path = Path(args.output)
        output_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        with output_path.open(
            "w", encoding="utf-8"
        ) as file:
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
