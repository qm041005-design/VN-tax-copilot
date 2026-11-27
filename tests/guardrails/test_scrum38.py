import copy
import json
import unittest
from unittest.mock import Mock

import httpx

from ai_engine.guardrails import ResearchContext, SafeResearchInput, run_guarded_research
from ai_engine.guardrails.llm_assessor import make_assessor
from ai_engine.guardrails.provider_errors import SafeProviderError
from ai_engine.providers.chat_json import ChatConfig, ChatJSON, json_object
from ai_engine.synthesis.backend_adapter import make_guarded_generator


def passage():
    return dict(passage_id="s1", text="Nguồn giả lập", legal_identifier="TEST/2099",
                effective_date="2099-01-01", version="test-v1", status="CON_HIEU_LUC")


def assessment():
    return {"context_complete": True, "query_supported": True, "conflicts_resolved": True,
            "assessments": [{"passage_id": "s1", "sufficient": True, "reason_code": "sufficient"}]}


def answer():
    result = {"status": "draft", "sections": {key: [] for key in
              ("issue", "facts", "authority", "analysis", "limitations", "next_steps")},
              "clarification_questions": [], "warnings": []}
    for key in ("authority", "analysis"):
        result["sections"][key] = [{"text": "Nhận định giả lập", "citation_ids": ["s1"]}]
    return result


def envelope(value, finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(value)}}]}


class TransportTests(unittest.TestCase):
    def config(self):
        return ChatConfig("https://provider.example.test/v1/chat/completions", "chosen-test-model", "test-secret")

    def provider(self, handler):
        return ChatJSON(self.config(), transport=httpx.MockTransport(handler))

    def test_http_contract_and_json_extraction(self):
        def handler(request):
            self.assertEqual(request.headers["authorization"], "Bearer test-secret")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "chosen-test-model")
            self.assertEqual(body["response_format"], {"type": "json_object"})
            return httpx.Response(200, json=envelope(answer()))
        self.assertEqual(self.provider(handler)([{"role": "user", "content": "JSON"}])["status"], "draft")
        self.assertNotIn("test-secret", repr(self.config()))

    def test_status_errors_sanitized(self):
        for status, code in ((401, "provider_auth"), (403, "provider_auth"), (429, "provider_rate_limit"),
                             (500, "provider_http"), (302, "provider_http")):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, text="test-secret a@example.test", headers={"Location": "https://other.test"})
            with self.subTest(status=status), self.assertRaises(SafeProviderError) as raised:
                self.provider(handler)([{"role": "user", "content": "JSON"}])
            self.assertEqual(str(raised.exception), code)
            self.assertEqual(len(calls), 1)

    def test_timeout_and_network_errors_sanitized(self):
        for exc, code in ((httpx.ReadTimeout("test-secret"), "provider_timeout"),
                          (httpx.ConnectError("test-secret"), "provider_network")):
            def handler(request):
                raise exc
            with self.assertRaises(SafeProviderError) as raised:
                self.provider(handler)([{"role": "user", "content": "JSON"}])
            self.assertEqual(str(raised.exception), code)

    def test_invalid_envelopes_and_truncation(self):
        for value in ({}, {"choices": []}, envelope(answer(), "length"),
                      {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]}):
            with self.subTest(value=value), self.assertRaises(SafeProviderError):
                self.provider(lambda request: httpx.Response(200, json=value))([{"role": "user", "content": "JSON"}])

    def test_duplicate_nonfinite_or_nonobject_json(self):
        for value in ('{"a":1,"a":2}', '{"n":NaN}', '[]', 'null'):
            with self.subTest(value=value), self.assertRaises(SafeProviderError):
                json_object(value)

    def test_invalid_or_unencrypted_configuration(self):
        for url in ("http://provider.test/api", "https://user:secret@provider.test/api", "https://provider.test/api?key=secret"):
            with self.assertRaises(SafeProviderError):
                ChatConfig(url, "model", "key")
        for timeout in (0, float("nan"), 121):
            with self.assertRaises(SafeProviderError):
                ChatConfig("https://provider.test/api", "model", "key", timeout)

    def test_request_limit_blocks_network(self):
        handler = Mock()
        with self.assertRaises(SafeProviderError) as raised:
            self.provider(handler)([{"role": "user", "content": "x" * 256001}])
        self.assertEqual(raised.exception.code, "provider_limit")
        handler.assert_not_called()

    def test_response_limit(self):
        with self.assertRaises(SafeProviderError) as raised:
            self.provider(lambda request: httpx.Response(200, content=b"x" * 1000001))([{"role": "user", "content": "JSON"}])
        self.assertEqual(raised.exception.code, "provider_limit")


class AssessorTests(unittest.TestCase):
    def safe(self, p=None):
        return SafeResearchInput("Câu hỏi", "2099", "Giả lập", (p or passage(),))

    def test_valid_assessment(self):
        result = make_assessor(lambda messages: assessment())(self.safe())
        self.assertTrue(result[0].sufficient)
        self.assertEqual(result[0].reason_code, "sufficient")

    def test_unknown_metadata_blocks_before_provider(self):
        for field, value in (("status", "CHUA_XAC_DINH"), ("effective_date", None), ("version", None), ("effective_date", "invalid")):
            p = passage()
            p[field] = value
            complete = Mock()
            result = make_assessor(complete)(self.safe(p))
            self.assertIsNone(result[0].sufficient)
            complete.assert_not_called()

    def test_query_level_insufficiency_overrides_source(self):
        for field, reason in (("context_complete", "missing_facts"), ("query_supported", "unsupported"), ("conflicts_resolved", "conflict")):
            data = assessment()
            data[field] = False
            result = make_assessor(lambda m: data)(self.safe())
            self.assertFalse(result[0].sufficient)
            self.assertEqual(result[0].reason_code, reason)

    def test_untrusted_assessment_shapes_blocked(self):
        cases = []
        for key, value in (("passage_id", "unknown"), ("sufficient", "true"), ("sufficient", 1), ("reason_code", "approved")):
            data = assessment()
            data["assessments"][0][key] = value
            cases.append(data)
        cases.extend([{}, {**assessment(), "query_supported": "true"}, {**assessment(), "assessments": []}])
        for data in cases:
            with self.subTest(data=data), self.assertRaises(SafeProviderError):
                make_assessor(lambda m: data)(self.safe())

    def test_one_uncertain_source_not_silently_discarded(self):
        safe = self.safe()
        p = passage()
        p.update(passage_id="s2", status="CHUA_XAC_DINH")
        complete = Mock()
        result = make_assessor(complete)(SafeResearchInput(safe.query, safe.tax_period, safe.material_facts, (*safe.passages, p)))
        self.assertTrue(all(a.sufficient is None for a in result))
        complete.assert_not_called()


class FlowTests(unittest.TestCase):
    def flow(self, completion, query="Câu hỏi", context=None):
        return run_guarded_research(query, [passage()], context or ResearchContext("2099", "Giả lập"),
                                    assess=make_assessor(completion), generate=make_guarded_generator(completion))

    def test_order_assess_then_generate(self):
        complete = Mock(side_effect=[assessment(), answer()])
        result = self.flow(complete)
        self.assertEqual(result.status, "draft")
        self.assertEqual(complete.call_count, 2)
        self.assertEqual(result.assessment_records[0]["decision"], "sufficient")

    def test_clarification_zero_provider_calls(self):
        complete = Mock()
        result = self.flow(complete, query="Thuế suất GTGT của hàng hóa?")
        self.assertEqual(result.status, "clarify")
        complete.assert_not_called()

    def test_insufficient_assessment_no_generation(self):
        data = assessment()
        data["query_supported"] = False
        complete = Mock(return_value=data)
        self.assertEqual(self.flow(complete).status, "abstain")
        self.assertEqual(complete.call_count, 1)

    def test_source_hallucination_and_approval_blocked(self):
        invalid = answer()
        invalid["sections"]["analysis"][0]["citation_ids"] = ["unknown"]
        approved = answer()
        approved["status"] = "approved"
        for value in (invalid, approved):
            self.assertEqual(self.flow(Mock(side_effect=[assessment(), value])).status, "abstain")

    def test_input_and_output_redacted(self):
        data = answer()
        data["sections"]["analysis"][0]["text"] = "Email a@example.test"
        complete = Mock(side_effect=[assessment(), data])
        r = self.flow(complete, query="Email a@example.test")
        self.assertNotIn("a@example.test", repr(complete.call_args_list))
        self.assertNotIn("a@example.test", repr(r))

    def test_provider_failure_at_both_phases(self):
        for effects in ([SafeProviderError("provider_timeout")], [assessment(), SafeProviderError("provider_auth")]):
            r = self.flow(Mock(side_effect=effects))
            self.assertEqual(r.status, "abstain")
            self.assertIn(r.reason, ("provider_timeout", "provider_auth"))
            self.assertIsNone(r.answer)

    def test_assessor_missing_facts_returns_clarify(self):
        data = assessment()
        data["context_complete"] = False
        complete = Mock(return_value=data)
        result = self.flow(complete)
        self.assertEqual(result.status, "clarify")
        self.assertTrue(result.questions)
        self.assertEqual(complete.call_count, 1)
