
import unittest

from evaluation.metrics.bm25_adapter import run_bm25_retrieval
from evaluation.metrics.recall_at_10 import calculate_recall_at_10


class TestBM25Adapter(unittest.TestCase):

    def test_bm25_retrieval_and_recall(self):
        benchmark = {
            "cases": [
                {
                    "case_id": "TEST-001",
                    "question": "thue gia tri gia tang",
                    "answerability": "answerable"
                }
            ]
        }

        passages = [
            {
                "passage_id": "P001",
                "text": "Quy dinh ve thue gia tri gia tang VAT"
            },
            {
                "passage_id": "P002",
                "text": "Quy dinh ve hop dong lao dong"
            }
        ]

        results = run_bm25_retrieval(benchmark, passages)

        self.assertEqual(results[0]["case_id"], "TEST-001")
        self.assertEqual(
            results[0]["retrieved_passage_ids"][0],
            "P001"
        )

        required_evidence = [
            {
                "evidence_id": "E001",
                "source_id": "TEST_SOURCE",
                "acceptable_passage_ids": ["P001"]
            }
        ]

        recall, evidence_results = calculate_recall_at_10(
            required_evidence,
            results[0]["retrieved_passage_ids"]
        )

        self.assertEqual(recall, 1.0)
        self.assertTrue(evidence_results[0]["found"])


if __name__ == "__main__":
    unittest.main()
