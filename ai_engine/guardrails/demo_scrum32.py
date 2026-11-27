"""Synthetic clarification demo: python -m ai_engine.guardrails.demo_scrum32."""
import json
from .research import ResearchContext, run_guarded_research
from .contract import to_contract


def main():
    for query in ("Thuế suất GTGT của hàng hóa này là bao nhiêu?", "Tôi có phải cá nhân cư trú không?"):
        result = run_guarded_research(query, [], ResearchContext("2099", "Tình huống giả lập"))
        print(query)
        print(json.dumps(to_contract(result), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
