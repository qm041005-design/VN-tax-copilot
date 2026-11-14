import copy
import json
import unittest
from unittest.mock import Mock

from ai_engine.guardrails import (
    SECTION_NAMES, EvidenceAssessment, ResearchContext, run_guarded_research,
    validate_output, to_contract, make_prompt_generator,
)


def output():
    data = {"status": "draft", "sections": {key: [] for key in SECTION_NAMES},
            "clarification_questions": [], "warnings": []}
    for key in ("authority", "analysis"):
        data["sections"][key] = [{"text": "Nội dung giả lập", "citation_ids": ["s1"]}]
    return data


class ContractTests(unittest.TestCase):
    def run_flow(self, payload):
        return run_guarded_research("Câu hỏi", [dict(passage_id="s1", text="Nguồn", legal_identifier="TEST")],
                                    ResearchContext("2099", "Giả lập"),
                                    assess=lambda safe: [EvidenceAssessment("s1", True)],
                                    generate=lambda safe: payload)

    def test_json_and_six_section_roundtrip(self):
        result = self.run_flow(json.dumps(output()))
        self.assertEqual(result.status, "draft")
        self.assertEqual(set(to_contract(result)["sections"]), set(SECTION_NAMES))
        self.assertEqual(result.citation_ids, ("s1",))

    def test_unknown_id_blocked(self):
        data = output()
        data["sections"]["analysis"][0]["citation_ids"] = ["unknown"]
        self.assertEqual(self.run_flow(data).status, "abstain")

    def test_missing_authority_or_analysis_blocked(self):
        for name in ("authority", "analysis"):
            data = output()
            data["sections"][name] = []
            self.assertEqual(self.run_flow(data).status, "abstain")

    def test_untrusted_status_blocked(self):
        data = output()
        data["status"] = "approved"
        self.assertEqual(self.run_flow(data).status, "abstain")

    def test_provider_clarify_cannot_publish_conclusion(self):
        data = output()
        data["status"] = "clarify"
        data["clarification_questions"] = ["Giao dịch xảy ra khi nào?"]
        result = self.run_flow(data)
        self.assertEqual(result.status, "clarify")
        self.assertIsNone(result.answer)
        self.assertTrue(all(not entries for entries in to_contract(result)["sections"].values()))

    def test_provider_abstain_has_no_answer(self):
        data = output()
        data["status"] = "abstain"
        self.assertIsNone(self.run_flow(data).answer)

    def test_clarify_needs_question(self):
        data = output()
        data["status"] = "clarify"
        self.assertEqual(self.run_flow(data).status, "abstain")

    def test_redacts_every_output_field(self):
        data = output()
        data["warnings"] = ["Liên hệ a@example.test"]
        data["sections"]["analysis"][0]["text"] = "CCCD 012345678901"
        result = self.run_flow(data)
        self.assertNotIn("a@example.test", repr(to_contract(result)))
        self.assertNotIn("012345678901", repr(result))
        self.assertIn("a@example.test", data["warnings"][0])

    def test_duplicate_json_keys_blocked(self):
        with self.assertRaises(ValueError):
            validate_output('{"status":"draft","status":"abstain"}', ["s1"])

    def test_uncited_legal_claim_blocked(self):
        data = output()
        data["sections"]["analysis"][0]["citation_ids"] = []
        self.assertEqual(self.run_flow(data).status, "abstain")

    def test_unknown_metadata_blocked(self):
        data = output()
        data["sections"]["analysis"][0]["url"] = "https://invented.test"
        self.assertEqual(self.run_flow(data).status, "abstain")

    def test_early_results_follow_contract(self):
        result = run_guarded_research("Question", [], ResearchContext())
        data = to_contract(result)
        self.assertEqual(data["status"], "clarify")
        self.assertTrue(data["clarification_questions"])
        self.assertEqual(set(data["sections"]), set(SECTION_NAMES))

    def test_prompt_bridge_receives_safe_input(self):
        build = Mock(return_value=[{"role": "user", "content": "safe"}])
        complete = Mock(return_value=output())
        result = run_guarded_research("Email a@example.test", [dict(passage_id="s1", text="Nguồn", legal_identifier="TEST")],
                                     ResearchContext("2099", "Giả lập"),
                                     assess=lambda safe: [EvidenceAssessment("s1", True)],
                                     generate=make_prompt_generator(build, complete))
        self.assertEqual(result.status, "draft")
        self.assertNotIn("a@example.test", repr(build.call_args))
        complete.assert_called_once()
