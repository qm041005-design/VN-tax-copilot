"""Run: python -m ai_engine.guardrails.demo_scrum23 (synthetic data only)."""
import json
from .research import ResearchContext, run_guarded_research
from .abstention import EvidenceAssessment
from .contract import SECTION_NAMES, to_contract


def main():
    passages = [{"passage_id": "demo-1", "legal_identifier": "TEST/2099",
                 "text": "Dữ liệu giả lập CCCD 012345678901, không phải văn bản pháp luật."}]
    context = ResearchContext("2099", "Tình huống giả lập")
    def assessor(safe):
        assert "012345678901" not in repr(safe)
        return [EvidenceAssessment("demo-1", True)]  # Fixture only, not a real assessment.
    def generator(safe):
        assert "012345678901" not in repr(safe)
        return {"status": "draft", "sections": {
            name: ([{"text": "Minh họa kỹ thuật với nguồn giả lập.", "citation_ids": ["demo-1"]}]
                   if name in ("authority", "analysis") else []) for name in SECTION_NAMES},
            "clarification_questions": [], "warnings": ["Chỉ dùng dữ liệu giả lập."]}
    scenarios = [
        ("Thiếu kỳ thuế/tình huống", passages, ResearchContext(), None),
        ("Không có nguồn", [], context, None),
        ("Nguồn hợp lệ trong fixture", passages, context, generator),
        ("AI dùng mã nguồn lạ", passages, context,
         lambda safe: {**generator(safe), "sections": {**generator(safe)["sections"],
                       "analysis": [{"text": "Kết luận giả lập", "citation_ids": ["unknown"]}]}}),
    ]
    for label, sources, ctx, generate in scenarios:
        result = run_guarded_research("Câu hỏi giả lập", sources, ctx, assess=assessor, generate=generate)
        print(label, '=>', result.status, '/', result.reason)
        print(json.dumps(to_contract(result), ensure_ascii=False))


if __name__ == '__main__':
    main()
