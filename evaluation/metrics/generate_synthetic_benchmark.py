
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "datasets"
ROOT.mkdir(parents=True, exist_ok=True)

categories = ["VAT", "CIT", "PIT", "TAX_ADMIN", "E_INVOICE"]

cases = []
passages = []

for number in range(1, 251):
    case_id = f"VN-TAX-{number:03d}"
    category = categories[(number - 1) % len(categories)]
    answerable = number <= 200
    passage_id = f"SYN-P{number:03d}"

    case = {
        "case_id": case_id,
        "question": f"Kiểm thử giả lập mã duy nhất SYNKEY{number:03d}",
        "category": category,
        "answerability": "answerable" if answerable else "unanswerable",
        "tax_period": None,
        "research_as_of": None,
        "required_evidence": (
            [{
                "evidence_id": f"SYN-E{number:03d}",
                "description": "Bằng chứng giả lập, không phải nguồn pháp luật",
                "source_id": f"SYN-S{number:03d}",
                "acceptable_passage_ids": [passage_id],
            }]
            if answerable else []
        ),
        "acceptable_conclusions": [],
        "assumptions": [],
        "material_claims": [],
        "tags": [],
        "reviewers": [
            {"reviewer_id": "SYN-REVIEWER-1", "decision": "pending"},
            {"reviewer_id": "SYN-REVIEWER-2", "decision": "pending"},
        ],
        "review_status": "draft",
    }

    cases.append(case)

    if answerable:
        passages.append({
            "passage_id": passage_id,
            "legal_identifier": f"SYN-{number:03d}",
            "article_title": f"Đoạn giả lập {number}",
            "text": f"Nội dung kiểm thử giả lập SYNKEY{number:03d}",
        })

benchmark = {
    "benchmark_version": "synthetic-test-1.0",
    "cases": cases,
}

files = {
    "benchmark_250_synthetic.json": benchmark,
    "passages_250_synthetic.json": passages,
}

for filename, data in files.items():
    path = ROOT / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Đã tạo: {path}")

print("200 answerable + 50 unanswerable (dữ liệu giả lập)")
