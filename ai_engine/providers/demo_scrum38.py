"""Offline HTTP simulation. No API keys, provider configuration or network needed."""
import json

import httpx

from ai_engine.guardrails import ResearchContext, run_guarded_research
from ai_engine.guardrails.llm_assessor import make_assessor
from ai_engine.synthesis.backend_adapter import make_guarded_generator
from .chat_json import ChatConfig, ChatJSON


def main():
    for mode in ("clarify", "insufficient", "draft", "unknown_id", "timeout", "auth"):
        calls = []
        def handler(request):
            calls.append(1)
            if mode == "timeout":
                raise httpx.ReadTimeout("simulated")
            if mode == "auth":
                return httpx.Response(401, text="simulated")
            if len(calls) == 1:
                result = {"context_complete": True, "query_supported": mode != "insufficient", "conflicts_resolved": True,
                          "assessments": [{"passage_id": "demo-1", "sufficient": True, "reason_code": "sufficient"}]}
            else:
                result = {"status": "draft", "sections": {key: [] for key in
                          ("issue", "facts", "authority", "analysis", "limitations", "next_steps")},
                          "clarification_questions": [], "warnings": []}
                for key in ("authority", "analysis"):
                    result["sections"][key] = [{"text": "Minh họa với nguồn giả lập.", "citation_ids": ["demo-1"]}]
                if mode == "unknown_id":
                    result["sections"]["analysis"][0]["citation_ids"] = ["outside-source-set"]
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})
        completion = ChatJSON(ChatConfig("https://offline.example.test/chat/completions", "simulated", "not-a-real-key"),
                              transport=httpx.MockTransport(handler))
        sources = [{"passage_id": "demo-1", "legal_identifier": "TEST/2099", "text": "Nguồn hoàn toàn giả lập.",
                    "effective_date": "2099-01-01", "version": "fixture-only", "status": "CON_HIEU_LUC"}]
        query = "Thuế suất GTGT hàng hóa?" if mode == "clarify" else "Câu hỏi kiểm thử giả lập"
        result = run_guarded_research(query, sources, ResearchContext("2099", "Giả lập"),
                                     assess=make_assessor(completion), generate=make_guarded_generator(completion))
        print(f"{mode}: status={result.status}, reason={result.reason}, simulated_http_calls={len(calls)}")


if __name__ == '__main__':
    main()
