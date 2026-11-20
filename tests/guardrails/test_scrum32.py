import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from ai_engine.guardrails import EvidenceAssessment, ResearchContext, run_guarded_research
from backend.app.services.guarded_research_service import research_from_rows


class Scrum32Tests(unittest.TestCase):
    def setUp(self):
        self.sources = [{"passage_id": "s1", "text": "Nguồn giả lập", "legal_identifier": "TEST",
                         "effective_date": "2099-01-01", "version": "chunk-v2", "status": "CHUA_XAC_DINH"}]
        self.assess = Mock(return_value=[EvidenceAssessment("s1", False, "temporal_unknown")])
        self.generate = Mock()

    def flow(self, query="Câu hỏi", context=None, **kwargs):
        return run_guarded_research(query, self.sources, context or ResearchContext("2099", "Giả lập"),
                                    assess=kwargs.get("assess", self.assess), generate=self.generate)

    def test_goods_specific_questions_before_ai(self):
        r = self.flow("Thuế suất GTGT của hàng hóa là bao nhiêu?")
        self.assertEqual(r.status, "clarify")
        self.assertTrue(any("Hàng hóa cụ thể" in q for q in r.questions))
        self.assertTrue(any("nhập khẩu" in q for q in r.questions))
        self.assertTrue(any("Giao dịch phát sinh" in q for q in r.questions))
        self.assess.assert_not_called()
        self.generate.assert_not_called()

    def test_residency_questions_do_not_request_identifiers(self):
        r = self.flow("Tôi có phải cá nhân cư trú không?")
        self.assertEqual(r.status, "clarify")
        self.assertTrue(any("hiện diện" in q for q in r.questions))
        self.assertTrue(any("chỗ ở" in q for q in r.questions))
        self.assertTrue(any("nước khác" in q for q in r.questions))
        self.assertFalse(any("CCCD" in q for q in r.questions))
        self.assess.assert_not_called()

    def test_only_missing_goods_field_asked(self):
        ctx = ResearchContext("2099", "Giả lập", scenario="goods_rate",
                              case_facts={"goods_description": "Mặt hàng giả lập", "transaction_type": "Bán nội địa"})
        r = self.flow(context=ctx)
        self.assertEqual(len(r.questions), 1)
        self.assertIn("Giao dịch phát sinh", r.questions[0])

    def test_structured_facts_are_redacted_before_assessor(self):
        ctx = ResearchContext("2099", None, scenario="goods_rate", case_facts={
            "goods_description": "Hàng giả lập a@example.test", "transaction_type": "Bán nội địa", "transaction_date": "2099-02"})
        r = self.flow(context=ctx)
        self.assertEqual(r.status, "abstain")
        self.assertNotIn("a@example.test", repr(self.assess.call_args))

    def test_assessment_log_has_source_identity_without_source_text(self):
        r = self.flow()
        log = r.assessment_records[0]
        self.assertEqual(log["decision"], "insufficient")
        self.assertEqual(log["reason_code"], "temporal_unknown")
        self.assertEqual(log["version"], "chunk-v2")
        self.assertEqual(len(log["snapshot_sha256"]), 64)
        self.assertNotIn("Nguồn giả lập", repr(log))
        self.generate.assert_not_called()

    def test_unknown_assessment_preserved(self):
        r = self.flow(assess=lambda s: [EvidenceAssessment("s1", None)])
        self.assertEqual(r.assessment_records[0]["decision"], "unknown")
        self.assertEqual(r.status, "abstain")

    def test_no_assessor_no_records_or_generation(self):
        r = self.flow(assess=None)
        self.assertEqual(r.assessment_records, ())
        self.generate.assert_not_called()

    def test_chunk_metadata_never_replaced_by_document(self):
        doc = SimpleNamespace(doc_code="TEST", version="doc-v1", effective_date=datetime(2090, 1, 1))
        chunk = SimpleNamespace(id=1, content="T", document=doc, effective_date=datetime(2099, 1, 1),
                                version="chunk-v2", status="CHUA_XAC_DINH", clause_number="0")
        assess = Mock(return_value=[])
        research_from_rows("q", [(chunk, 1)], tax_period="2099", material_facts="Giả lập", assess=assess)
        p = assess.call_args.args[0].passages[0]
        self.assertTrue(p["effective_date"].startswith("2099"))
        self.assertEqual(p["version"], "chunk-v2")
        self.assertEqual(p["document_version"], "doc-v1")
        self.assertIsNone(p["khoan"])
        chunk.effective_date = None
        chunk.version = None
        research_from_rows("q", [(chunk, 1)], tax_period="2099", material_facts="Giả lập", assess=assess)
        self.assertIsNone(assess.call_args.args[0].passages[0]["effective_date"])
        self.assertIsNone(assess.call_args.args[0].passages[0]["version"])

    def test_unknown_fact_is_still_missing(self):
        ctx = ResearchContext("2099", "Giả lập", scenario="goods_rate", case_facts={
            "goods_description": "chưa biết", "transaction_type": "Nội địa", "transaction_date": "2099-01"})
        r = self.flow(context=ctx)
        self.assertEqual(len(r.questions), 1)
        self.assertIn("Hàng hóa cụ thể", r.questions[0])
