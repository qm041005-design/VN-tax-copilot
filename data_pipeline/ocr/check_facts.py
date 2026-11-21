#!/usr/bin/env python3
"""Kiểm tra các con số/mốc trọng yếu có xuất hiện đúng trong kết quả OCR không.

    python -m data_pipeline.ocr.check_facts --ocr-dir data_pipeline/local_data/ocr
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_FACTS = Path(__file__).resolve().parents[1] / "evidence" / "ocr_critical_facts.json"


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t)).strip()


def check_facts(text: str, facts: list[str]) -> dict:
    t = _norm(text)
    missing = [f for f in facts if _norm(f) not in t]
    return {"total": len(facts), "found": len(facts) - len(missing), "missing": missing}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-dir", required=True, help="thư mục chứa <id>/<id>.txt")
    ap.add_argument("--facts", default=str(DEFAULT_FACTS))
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    facts = {k: v for k, v in json.loads(Path(a.facts).read_text("utf-8")).items() if not k.startswith("_")}
    out, ok = {}, True
    for law, items in facts.items():
        f = Path(a.ocr_dir) / law / f"{law}.txt"
        if not f.exists():
            print(f"✗ {law}: chưa có {f}"); ok = False; continue
        out[law] = check_facts(f.read_text("utf-8"), items)
        r = out[law]
        print(f"{law}: {r['found']}/{r['total']} đúng" + (f"  THIẾU: {r['missing']}" if r["missing"] else ""))
        ok &= not r["missing"]
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
