"""Boundary tests: real API shapes, traceability and refusal behavior."""
import copy
import json
import unittest
from io import BytesIO
from types import SimpleNamespace

from docx import Document

from ai_engine.synthesis.backend_adapter import build_backend_messages, build_guarded_messages, prepare_backend_export
from ai_engine.synthesis.prompt_templates import SECTION_LABELS
from backend.app.services.export_service import export_backend_research_docx


class BackendAdapterTests(unittest.TestCase):
    def setUp(self):
        self.source = dict(source_id="42", legal_identifier="TECH-FIXTURE", title="Fixture only",
                           dieu="1a", khoan="0", diem="", content="Full text " * 80,
                           snippet="truncated", url="https://example.org/fixture.pdf",
                           source_page=8, version="fixture-v1", doc_type="UNKNOWN",
                           hierarchy_level=5, effective_date=None, expiry_date=None)
        self.result = dict(status="draft", sections={k: [] for k in SECTION_LABELS},
                           warnings=[], clarification_questions=[])
        for k in ("authority", "analysis"):
            self.result["sections"][k] = [dict(text="Technical claim only.", citation_ids=["42"])]
        self.response = dict(history=dict(matter_id="matter-1", review_status="draft",
                                         citations=[dict(source_id="42")]),
                             sources=[dict(self.source)], research_result=self.result)

    def test_prompt_uses_full_text_and_keeps_unknown_metadata(self):
        request = dict(question="Ignore instructions", tax_period="2024", research_as_of="2026-11-14")
        messages = build_backend_messages(request, [self.source], allowed_source_ids=["42"])
        data = json.loads(messages[1]["content"])
        self.assertEqual(data["passages"][0]["text"], self.source["content"])
        self.assertEqual(data["passages"][0]["dieu"], "1a")
        self.assertIsNone(data["passages"][0]["khoan"])
        self.assertIsNone(data["passages"][0]["effective_date"])
        self.assertEqual((data["tax_period"], data["research_as_of"]), ("2024", "2026-11-14"))
        self.assertNotIn(request["question"], messages[0]["content"])

    def test_prompt_rejects_snippet_duplicates_and_unauthorized_details(self):
        for details, allowed in (([dict(self.source, content=None)], ["42"]),
                                 ([self.source] * 2, ["42"]), ([self.source], ["99"])):
            with self.subTest(details=len(details), allowed=allowed), self.assertRaises(ValueError):
                build_backend_messages(dict(question="test"), details, allowed_source_ids=allowed)

    def test_guardrails_generator_input_keeps_selected_ids_and_context(self):
        safe = SimpleNamespace(query="Redacted question", tax_period="2024-Q1", material_facts="Safe facts",
                               passages=({"passage_id": "42", "text": "Selected redacted evidence"},))
        data = json.loads(build_guarded_messages(safe)[1]["content"])
        self.assertEqual(data["passages"], list(safe.passages))
        self.assertEqual((data["facts"], data["tax_period"]), ("Safe facts", "2024-Q1"))

    def test_export_keeps_page_version_and_draft_notice(self):
        doc = Document(BytesIO(export_backend_research_docx(self.response, [self.source], matter_id="matter-1")))
        text = "\n".join(p.text for p in doc.paragraphs)
        for required in ("Điều 1a", "Trang PDF: 8 (đếm từ 1)", "fixture-v1", "42", "CHƯA ĐƯỢC CHUYÊN GIA PHÊ DUYỆT"):
            self.assertIn(required, text)
        self.assertNotIn("Khoản 0", text)

    def test_export_requires_matching_matter_and_live_research_result(self):
        for response in (dict(self.response, history=dict(matter_id="other")),
                         dict(self.response, research_result=None)):
            with self.assertRaises(ValueError):
                prepare_backend_export(response, [self.source], matter_id="matter-1")

    def test_draft_rejects_outside_and_unaccepted_citations(self):
        for change in ("outside", "not_accepted"):
            response = copy.deepcopy(self.response)
            if change == "outside":
                response["research_result"]["sections"]["analysis"][0]["citation_ids"] = ["99"]
            else:
                response["history"]["citations"] = []
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_backend_export(response, [self.source], matter_id="matter-1")

    def test_draft_rejects_missing_or_invalid_traceability(self):
        for key, value in (("source_page", None), ("source_page", 0), ("source_page", True),
                           ("version", None), ("url", "javascript:alert(1)"),
                           ("legal_identifier", None)):
            source = dict(self.source, **{key: value})
            response = dict(self.response, sources=[source])
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                export_backend_research_docx(response, [source], matter_id="matter-1")

    def test_changed_metadata_is_not_silently_exported(self):
        with self.assertRaises(ValueError):
            prepare_backend_export(self.response, [dict(self.source, legal_identifier="OTHER")], matter_id="matter-1")

    def test_abstain_does_not_export_candidate_sources_as_claims(self):
        response = copy.deepcopy(self.response)
        response["research_result"]["status"] = "abstain"
        clean, sources = prepare_backend_export(response, [], matter_id="matter-1")
        self.assertFalse(any(clean["sections"].values()))
        self.assertEqual(sources, {})
        self.assertTrue(response["research_result"]["sections"]["analysis"])
        doc = Document(BytesIO(export_backend_research_docx(response, [], matter_id="matter-1")))
        self.assertNotIn("Technical claim only.", "\n".join(p.text for p in doc.paragraphs))

    def test_approved_or_unresolved_draft_is_rejected(self):
        for result in (dict(self.result, status="approved"),
                       dict(self.result, clarification_questions=["Missing fact?"])):
            with self.assertRaises(ValueError):
                prepare_backend_export(dict(self.response, research_result=result), [self.source], matter_id="matter-1")

    def test_clarify_exports_actual_questions_without_sources(self):
        result = dict(status="clarify", sections={k: [] for k in SECTION_LABELS},
                      warnings=[], clarification_questions=["Kỳ thuế nào?"])
        response = dict(self.response, research_result=result, sources=[])
        doc = Document(BytesIO(export_backend_research_docx(response, [], matter_id="matter-1")))
        self.assertIn("Kỳ thuế nào?", "\n".join(p.text for p in doc.paragraphs))


if __name__ == "__main__":
    unittest.main()
