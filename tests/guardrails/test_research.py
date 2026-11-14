import unittest
from unittest.mock import Mock

from ai_engine.guardrails import (
    Claim, EvidenceAssessment, GeneratedResearch, ResearchContext,
    run_guarded_research, validate_citations,
)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.hits = [dict(passage_id="s1", legal_identifier="TEST/2099", text="Nguồn giả lập", secret="do not send")]
        self.context = ResearchContext("2099", "Giao dịch giả lập")
        self.assess = Mock(return_value=[EvidenceAssessment("s1", True)])
        self.generate = Mock(return_value=GeneratedResearch((Claim("Nguồn giả lập", ("s1",), "authority"), Claim("Nhận định giả lập", ("s1",)),)))

    def run_flow(self, **kwargs):
        args = dict(query="Câu hỏi", passages=self.hits, context=self.context,
                    assess=self.assess, generate=self.generate)
        args.update(kwargs)
        return run_guarded_research(**args)

    def test_missing_context_never_calls_ai(self):
        result = self.run_flow(context=ResearchContext())
        self.assertEqual(result.status, "clarify")
        self.assertEqual(len(result.questions), 2)
        self.assess.assert_not_called()
        self.generate.assert_not_called()

    def test_blank_query(self):
        self.assertEqual(self.run_flow(query=" ").reason, "empty_query")
        self.generate.assert_not_called()

    def test_general_question_policy(self):
        ctx = ResearchContext(require_tax_period=False, require_material_facts=False)
        self.assertEqual(self.run_flow(context=ctx).status, "draft")

    def test_no_sources(self):
        self.assertEqual(self.run_flow(passages=[]).reason, "no_evidence")
        self.assess.assert_not_called()
        self.generate.assert_not_called()

    def test_invalid_source_before_external_call(self):
        self.assertEqual(self.run_flow(passages=self.hits * 2).status, "abstain")
        self.assess.assert_not_called()

    def test_default_no_assessor(self):
        self.assertEqual(self.run_flow(assess=None).reason, "assessment_unavailable")
        self.generate.assert_not_called()

    def test_insufficient_evidence(self):
        self.assess.return_value = [EvidenceAssessment("s1", False)]
        self.assertEqual(self.run_flow().reason, "insufficient_evidence")
        self.generate.assert_not_called()

    def test_only_selected_sources_reach_generation(self):
        self.hits.append(dict(passage_id="s2", legal_identifier="TEST2/2099", text="Không đủ căn cứ"))
        self.assertEqual(self.run_flow().status, "draft")
        self.assertEqual([p["passage_id"] for p in self.generate.call_args.args[0].passages], ["s1"])

    def test_unselected_source_citation_blocked(self):
        self.hits.append(dict(passage_id="s2", legal_identifier="TEST2/2099", text="Không đủ căn cứ"))
        self.generate.return_value = GeneratedResearch((Claim("claim", ("s2",)),))
        result = self.run_flow()
        self.assertEqual(result.reason, "invalid_citations")
        self.assertIsNone(result.answer)

    def test_empty_and_hallucinated_citations(self):
        for ids in ((), ("unknown",), (True,), (1,)):
            self.generate.return_value = GeneratedResearch((Claim("claim", ids),))
            self.assertEqual(self.run_flow().reason, "invalid_citations")

    def test_every_claim_requires_citation(self):
        self.generate.return_value = GeneratedResearch((Claim("a", ("s1",)), Claim("b", ())))
        self.assertEqual(self.run_flow().reason, "invalid_citations")

    def test_redaction_at_each_boundary(self):
        self.hits[0]["text"] = "CCCD 012345678901"
        ctx = ResearchContext("2099", "Liên hệ a@example.test")
        self.generate.return_value = GeneratedResearch((Claim("Nguồn", ("s1",), "authority"), Claim("Email a@example.test", ("s1",)),))
        result = self.run_flow(query="MST 0123456789", context=ctx)
        for callback in (self.assess, self.generate):
            sent = repr(callback.call_args.args[0])
            for secret in ("0123456789", "a@example.test", "do not send"):
                self.assertNotIn(secret, sent)
        self.assertNotIn("a@example.test", result.answer)
        self.assertEqual(self.hits[0]["text"], "CCCD 012345678901")

    def test_provider_error_does_not_leak(self):
        self.generate.side_effect = RuntimeError("PII a@example.test")
        result = self.run_flow()
        self.assertEqual(result.status, "abstain")
        self.assertNotIn("a@example.test", repr(result))

    def test_missing_generator(self):
        self.assertEqual(self.run_flow(generate=None).reason, "generation_unavailable")

    def test_malformed_assessment(self):
        self.assess.return_value = [{"passage_id": "s1", "sufficient": True}]
        self.assertEqual(self.run_flow().status, "abstain")
        self.generate.assert_not_called()

    def test_id_type_strictness(self):
        self.assertFalse(validate_citations(GeneratedResearch((Claim("c", (True,)),)), (1,)))
        self.assertFalse(validate_citations(GeneratedResearch((Claim("c", ("1",)),)), (1,)))

    def test_mutation_cannot_expand_allowed_sources(self):
        def malicious_callback(safe):
            safe.passages[0]["passage_id"] = "evil"
            return GeneratedResearch((Claim("c", ("evil",)),))
        self.assertEqual(self.run_flow(generate=malicious_callback).reason, "invalid_citations")
