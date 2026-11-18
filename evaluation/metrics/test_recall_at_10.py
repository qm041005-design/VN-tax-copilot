
import unittest
from evaluation.metrics.recall_at_10 import evaluate


def make_benchmark():
    cases = []
    retrieval = []

    for i in range(1, 251):
        case_id = f"VN-TAX-{i:03d}"
        answerable = i <= 200

        if i <= 60:
            category = "VAT"
        elif i <= 120:
            category = "CIT"
        elif i <= 180:
            category = "PIT"
        else:
            category = "TAX_ADMIN"

        evidence_id = f"E{i:03d}"
        passage_id = f"P{i:03d}"
        tags = []

        if i <= 40:
            tags.append("historical")

        if 41 <= i <= 70:
            tags.append("conflicting_sources")
        cases.append({
            "case_id": case_id,
            "question": f"Synthetic test question {i}",
            "tags": tags,
            "category": category,
            "answerability": (
                "answerable" if answerable else "unanswerable"
            ),
            "tax_period": None,
            "required_evidence": (
                [{
                    "evidence_id": evidence_id,
                    "description": "Synthetic evidence",
                    "source_id": "TEST_SOURCE",
                    "acceptable_passage_ids": [passage_id]
                }] if answerable else []
            ),
            "acceptable_conclusions": [],
            "assumptions": [],
            "material_claims": [],
            "reviewers": [
                {"reviewer_id": "TEST_R1", "decision": "approved"},
                {"reviewer_id": "TEST_R2", "decision": "approved"}
            ],
            "review_status": "approved"
        })

        if answerable:
            retrieval.append({
                "case_id": case_id,
                "retrieved_passage_ids": [passage_id]
            })

    return {
        "benchmark_version": "synthetic-test",
        "cases": cases
    }, retrieval


class TestRecallAt10(unittest.TestCase):

    def test_pass(self):
        benchmark, retrieval = make_benchmark()

        report = evaluate(benchmark, retrieval)

        self.assertEqual(report["at03_status"], "PASS")
        self.assertTrue(report["benchmark_valid"])
        self.assertEqual(report["macro_recall_at_10"], 1.0)

    def test_fail(self):
        benchmark, retrieval = make_benchmark()

        for result in retrieval[:40]:
            result["retrieved_passage_ids"] = []

        report = evaluate(benchmark, retrieval)

        self.assertEqual(report["at03_status"], "FAIL")
        self.assertTrue(report["benchmark_valid"])
        self.assertAlmostEqual(
            report["macro_recall_at_10"], 0.80
        )

    def test_missing_source(self):
        benchmark, retrieval = make_benchmark()

        del benchmark["cases"][0]["required_evidence"][0]["source_id"]

        report = evaluate(benchmark, retrieval)

        self.assertEqual(
            report["at03_status"], "NOT_EVALUATED"
        )

    def test_duplicate_reviewer(self):
        benchmark, retrieval = make_benchmark()

        benchmark["cases"][0]["reviewers"][1]["reviewer_id"] = "TEST_R1"

        report = evaluate(benchmark, retrieval)

        self.assertEqual(
            report["at03_status"], "NOT_EVALUATED"
        )


    def test_missing_admin_invoice_cases(self):
        benchmark, retrieval = make_benchmark()

        for case in benchmark["cases"]:
            if case["category"] == "TAX_ADMIN":
                case["category"] = "VAT"

        report = evaluate(benchmark, retrieval)

        self.assertEqual(report["at03_status"], "NOT_EVALUATED")
        self.assertFalse(report["benchmark_valid"])

    def test_missing_special_cases(self):
        benchmark, retrieval = make_benchmark()

        for case in benchmark["cases"]:
            case["tags"] = []

        report = evaluate(benchmark, retrieval)

        self.assertEqual(report["at03_status"], "NOT_EVALUATED")
        self.assertFalse(report["benchmark_valid"])

    def test_missing_required_question(self):
        benchmark, retrieval = make_benchmark()

        del benchmark["cases"][0]["question"]

        report = evaluate(benchmark, retrieval)

        self.assertEqual(report["at03_status"], "NOT_EVALUATED")
        self.assertFalse(report["benchmark_valid"])

    def test_special_tags_moved_to_unanswerable(self):
        benchmark, retrieval = make_benchmark()

        # Xoa tat ca nhan dac biet
        for case in benchmark["cases"]:
            case["tags"] = []

        # Chuyen nhan sang 50 cau unanswerable
        for case in benchmark["cases"]:
            if case["answerability"] == "unanswerable":
                case["tags"] = [
                    "historical",
                    "amendment",
                    "conflicting_sources"
                ]

        report = evaluate(benchmark, retrieval)

        self.assertEqual(
            report["at03_status"], "NOT_EVALUATED"
        )
        self.assertFalse(report["benchmark_valid"])

    def test_special_tags_only_in_unanswerable(self):
        benchmark, retrieval = make_benchmark()

        for case in benchmark["cases"]:
            if case["answerability"] == "answerable":
                case["tags"] = []
            else:
                case["tags"] = [
                    "historical",
                    "amendment",
                    "conflicting_sources"
                ]

        report = evaluate(benchmark, retrieval)

        self.assertEqual(
            report["at03_status"], "NOT_EVALUATED"
        )
        self.assertFalse(report["benchmark_valid"])


if __name__ == "__main__":
    unittest.main()
