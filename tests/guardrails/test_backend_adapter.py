import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.services.guarded_research_service import research_from_rows
from ai_engine.guardrails import Claim, GeneratedResearch, EvidenceAssessment


class BackendAdapterTests(unittest.TestCase):
    def test_full_content_and_database_id_used(self):
        chunk = SimpleNamespace(id=42, document=SimpleNamespace(doc_code="TEST/2099"),
                                content="Nguồn giả lập CCCD 012345678901")
        assess = Mock(return_value=[EvidenceAssessment("42", True)])
        generate = Mock(return_value=GeneratedResearch((Claim("Nguồn giả lập", ("42",), "authority"), Claim("Nhận định giả lập", ("42",)),)))
        result = research_from_rows("Tra cứu", [(chunk, 99)], tax_period="2099",
                                    material_facts="Giao dịch giả lập", assess=assess, generate=generate)
        self.assertEqual(result.status, "draft")
        self.assertEqual(result.citation_ids, ("42",))
        self.assertNotIn("012345678901", repr(assess.call_args))

    def test_default_blocks_generation(self):
        result = research_from_rows("Tra cứu", [], tax_period="2099", material_facts="Giả lập")
        self.assertEqual(result.status, "abstain")
