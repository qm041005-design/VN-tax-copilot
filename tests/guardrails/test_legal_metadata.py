import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ai_engine.guardrails import prepare_research
from ai_engine.guardrails.legal_metadata import normalize_clause_number
from backend.app.services.guarded_research_service import research_from_rows


class ClauseNumberTests(unittest.TestCase):
    def test_absent_values(self):
        for value in (None, 0, "0", "", " ", " 0 ", "\t\n"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_clause_number(value))

    def test_real_clauses_remain_strings(self):
        for value, expected in ((1, "1"), ("1", "1"), ("1a", "1a"), (" 1a ", "1a")):
            with self.subTest(value=value):
                self.assertEqual(normalize_clause_number(value), expected)

    def test_pipeline_normalizes_before_assessment(self):
        for value in (0, "0", "", " ", None):
            result = prepare_research("q", [{"passage_id": "s1", "text": "t", "legal_identifier": "TEST", "khoan": value}])
            self.assertIsNone(result.passages[0]["khoan"])

    def test_backend_adapter_emits_null_or_alphanumeric(self):
        for value, expected in ((0, None), ("0", None), ("", None), (" ", None), (None, None), ("1a", "1a")):
            with self.subTest(value=value):
                chunk = SimpleNamespace(id=1, content="Nguồn giả lập", clause_number=value,
                                        document=SimpleNamespace(doc_code="TEST"))
                assess = Mock(return_value=[])
                research_from_rows("q", [(chunk, 1)], tax_period="2099", material_facts="Giả lập", assess=assess)
                self.assertEqual(assess.call_args.args[0].passages[0]["khoan"], expected)
