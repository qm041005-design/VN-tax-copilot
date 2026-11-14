import unittest

from ai_engine.guardrails import prepare_research


class PipelineTests(unittest.TestCase):
    def test_redacts_query_sources_and_drops_metadata_without_mutation(self):
        hits = [dict(passage_id=1, text="CCCD 012345678901", legal_identifier="TEST/2099",
                     client_email="a@example.test", score=999)]
        prepared = prepare_research("MST: 0123456789", hits)
        self.assertNotIn("0123456789", repr(prepared))
        self.assertNotIn("a@example.test", repr(prepared))
        self.assertNotIn("score", prepared.passages[0])
        self.assertEqual(hits[0]["text"], "CCCD 012345678901")

    def test_rejects_sensitive_id(self):
        with self.assertRaises(ValueError):
            prepare_research("thuế", [dict(passage_id="a@example.test")])
