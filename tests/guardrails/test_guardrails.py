import unittest

from ai_engine.guardrails import EvidenceAssessment, decide_abstention, redact_text


class RedactionTests(unittest.TestCase):
    def test_identifiers(self):
        cases = [
            ("CCCD: 012345678901", "CCCD"),
            ("CMND: 123456789", "CMND"),
            ("MST: 0123456789", "MST"),
            ("mã số thuế: 0123456789-001", "MST"),
            ("0123456789-001", "MST"),
            ("0123456789", "MST"),
            ("an@example.test", "EMAIL"),
            ("0912 345 678", "PHONE"),
            ("+84 912 345 678", "PHONE"),
            ("0084 912 345 678", "PHONE"),
            ("０１２３４５６７８９０１", "CCCD"),
        ]
        for raw, kind in cases:
            with self.subTest(raw=raw):
                result = redact_text(raw)
                self.assertIn(f"[REDACTED_{kind}]", result.text)
                self.assertEqual(result.counts, {kind: 1})

    def test_legal_numbers_and_dates_preserved(self):
        text = "Điều 12 khoản 3, 01/2099/NĐ-CP, ngày 11/11/2099, thuế 10%."
        self.assertEqual(redact_text(text).text, text)

    def test_label_priority_and_idempotence(self):
        result = redact_text("MST: 0912345678; a@example.test; a@example.test")
        self.assertEqual(result.counts, {"MST": 1, "EMAIL": 2})
        self.assertEqual(redact_text(result.text).text, result.text)
        self.assertNotIn("0912345678", repr(result))

    def test_long_number_not_partially_redacted(self):
        self.assertEqual(redact_text("123456789012345").text, "123456789012345")

    def test_type(self):
        with self.assertRaises(TypeError):
            redact_text(None)


class AbstentionTests(unittest.TestCase):
    def setUp(self):
        self.hits = [dict(passage_id=1, legal_identifier="TEST/2099", text="Nguồn giả lập", score=999)]

    def test_no_query_or_sources(self):
        self.assertEqual(decide_abstention(" ", self.hits).reason, "empty_query")
        self.assertEqual(decide_abstention("thuế", []).reason, "no_evidence")

    def test_high_score_does_not_allow(self):
        self.assertTrue(decide_abstention("thuế", self.hits).should_abstain)

    def test_explicit_sufficiency(self):
        decision = decide_abstention("thuế", self.hits, [EvidenceAssessment(1, True)])
        self.assertFalse(decision.should_abstain)
        self.assertEqual(decision.evidence_ids, (1,))

    def test_false_unknown_and_truthy_values(self):
        for value in (False, None, "true", 1):
            self.assertTrue(decide_abstention("thuế", self.hits, [EvidenceAssessment(1, value)]).should_abstain)

    def test_missing_source_metadata(self):
        for key in ("text", "legal_identifier", "passage_id"):
            hit = self.hits[0].copy()
            del hit[key]
            self.assertTrue(decide_abstention("thuế", [hit], [EvidenceAssessment(1, True)]).should_abstain)

    def test_duplicate_and_unknown_ids(self):
        self.assertTrue(decide_abstention("thuế", self.hits * 2).should_abstain)
        for assessments in ([EvidenceAssessment(2, True)], [EvidenceAssessment(1, True)] * 2):
            self.assertTrue(decide_abstention("thuế", self.hits, assessments).should_abstain)


if __name__ == "__main__":
    unittest.main()
