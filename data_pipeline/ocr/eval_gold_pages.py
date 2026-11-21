#!/usr/bin/env python3
"""So OCR từng trang với bản chuẩn theo trang: gold_pages/<law-id>_pNNN.txt.

    python -m data_pipeline.ocr.eval_gold_pages --ocr-dir <thư mục OCR> [--gold-dir ...] [--json out.json]
Bản chuẩn trong repo là bản chép sơ bộ từ ảnh, CẦN người rà soát trước khi dùng nghiệm thu.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .evaluate_ocr import evaluate

DEFAULT_GOLD = Path(__file__).resolve().parents[1] / "evidence" / "gold_pages"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-dir", required=True)
    ap.add_argument("--gold-dir", default=str(DEFAULT_GOLD))
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    rows = {}
    for g in sorted(Path(a.gold_dir).glob("*_p*.txt")):
        m = re.match(r"(.+)_p(\d+)$", g.stem)
        law, page = m.group(1), int(m.group(2))
        hyp = Path(a.ocr_dir) / law / f"page_{page:03d}.txt"
        if not hyp.exists():
            print(f"thiếu {hyp}", file=sys.stderr); continue
        r = evaluate(g.read_text("utf-8"), hyp.read_text("utf-8"))
        rows[g.stem] = r
        print(f"{g.stem}: CER={r['cer']*100:.2f}%  WER={r['wer']*100:.2f}%  "
              f"CER-không-dấu={r['base_cer_no_diacritics']*100:.2f}%  "
              f"ký-tự-có-dấu-đúng={r['diacritic_char_accuracy']*100:.2f}%  lỗi-chỉ-sai-dấu={r['diacritic_only_errors']}")
    if rows:
        tot = sum(r["ref_chars"] for r in rows.values())
        w = lambda k: sum(r[k] * r["ref_chars"] for r in rows.values()) / tot
        print(f"TỔNG ({tot} ký tự): CER={w('cer')*100:.2f}%  CER-không-dấu={w('base_cer_no_diacritics')*100:.2f}%  "
              f"ký-tự-có-dấu-đúng={w('diacritic_char_accuracy')*100:.2f}%")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
