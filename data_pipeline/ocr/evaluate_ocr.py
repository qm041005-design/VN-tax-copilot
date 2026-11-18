#!/usr/bin/env python3
"""Đánh giá chất lượng OCR tiếng Việt: CER/WER, độ chính xác dấu, chuẩn Unicode NFC,
và bảo toàn cấu trúc pháp lý (Điều/Khoản/Điểm).

    python -m data_pipeline.ocr.evaluate_ocr --ref-dir data/gold --hyp-dir data/ocr --report report.md
    python -m data_pipeline.ocr.evaluate_ocr --ref gold.txt --hyp ocr.txt

Ngưỡng đạt mặc định là ĐỀ XUẤT, cần nhóm xác nhận (chỉnh bằng tham số dòng lệnh).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

_VI = "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵđ"
VI_LETTERS = set(_VI + _VI.upper())
ALLOWED = (VI_LETTERS | set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
           | set("0123456789") | set(" \t\n") | set("!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~\\")
           | set("–—‘’“”…°§€₫•·²³"))

# Tiêu đề Điều: OCR hay đọc dấu chấm sau số Điều thành ',' ':' ';' ("Điều 1, Phạm vi...").
# Không nhận dòng tham chiếu như "Điều 2 của Luật này" (không có dấu câu ngay sau số).
ARTICLE_RE = re.compile(r"(?m)^\s*Điều\s+(\d+[a-z]?)\s*[.,:;]")

DEFAULT_THRESHOLDS = {"cer": 0.05, "diacritic_char_accuracy": 0.97, "article_recall": 0.95}


def strip_marks(s: str) -> str:
    """Bỏ dấu thanh/mũ nhưng giữ độ dài (mỗi ký tự NFC -> đúng 1 ký tự gốc)."""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def collapse(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t)).strip()


def unicode_report(raw: str) -> dict:
    nonspace = [c for c in raw if not c.isspace()]
    foreign = Counter(c for c in nonspace if c not in ALLOWED)
    return {
        "is_nfc": unicodedata.is_normalized("NFC", raw),
        "combining_marks": sum(unicodedata.category(c) == "Mn" for c in raw),
        "replacement_chars": raw.count("\ufffd"),
        "private_use_chars": sum(unicodedata.category(c) == "Co" for c in raw),
        "control_chars": sum(unicodedata.category(c) == "Cc" and c not in "\n\t\r" for c in raw),
        "foreign_char_ratio": round(sum(foreign.values()) / max(len(nonspace), 1), 5),
        "top_foreign_chars": foreign.most_common(8),
    }


def diacritic_stats(ref: str, hyp: str) -> dict:
    """Trên các ký tự gốc có dấu: bao nhiêu được nhận đúng; bao nhiêu lỗi 'chỉ sai dấu'."""
    marked_total = sum(1 for c in ref if c != strip_marks(c))
    marked_ok = diacritic_only = 0
    for op in Levenshtein.opcodes(ref, hyp):
        n_src = op.src_end - op.src_start
        if op.tag == "equal":
            marked_ok += sum(1 for c in ref[op.src_start:op.src_end] if c != strip_marks(c))
        elif op.tag == "replace" and n_src == op.dest_end - op.dest_start:
            for a, b in zip(ref[op.src_start:op.src_end], hyp[op.dest_start:op.dest_end]):
                if a != b and strip_marks(a) == strip_marks(b):
                    diacritic_only += 1
    return {"marked_chars": marked_total,
            "diacritic_char_accuracy": round(marked_ok / marked_total, 5) if marked_total else 1.0,
            "diacritic_only_errors": diacritic_only}


def structure_stats(ref_raw: str, hyp_raw: str) -> dict:
    nfc = lambda t: unicodedata.normalize("NFC", t)
    ref_raw, hyp_raw = nfc(ref_raw), nfc(hyp_raw)
    art = ARTICLE_RE
    ref_a, hyp_a = set(art.findall(ref_raw)), set(art.findall(hyp_raw))
    khoan = re.compile(r"(?m)^\s*\d+\.\s")
    diem = re.compile(r"(?m)^\s*[a-zđ]\)\s")
    ratio = lambda r, h: round(min(len(h), len(r)) / len(r), 5) if r else 1.0
    return {"articles_ref": len(ref_a),
            "article_recall": round(len(ref_a & hyp_a) / len(ref_a), 5) if ref_a else 1.0,
            "missing_articles": sorted(ref_a - hyp_a),
            "khoan_ratio": ratio(khoan.findall(ref_raw), khoan.findall(hyp_raw)),
            "diem_ratio": ratio(diem.findall(ref_raw), diem.findall(hyp_raw))}


def evaluate(ref_raw: str, hyp_raw: str, th: dict | None = None) -> dict:
    th = {**DEFAULT_THRESHOLDS, **(th or {})}
    ref, hyp = collapse(ref_raw), collapse(hyp_raw)
    rw, hw = ref.split(), hyp.split()
    m = {
        "ref_chars": len(ref),
        "cer": round(Levenshtein.distance(ref, hyp) / max(len(ref), 1), 5),
        "wer": round(Levenshtein.distance(rw, hw) / max(len(rw), 1), 5),
        "base_cer_no_diacritics": round(
            Levenshtein.distance(strip_marks(ref), strip_marks(hyp)) / max(len(ref), 1), 5),
    }
    m.update(diacritic_stats(ref, hyp))
    m["unicode"] = unicode_report(hyp_raw)
    m["structure"] = structure_stats(ref_raw, hyp_raw)
    u = m["unicode"]
    checks = {
        "cer": m["cer"] <= th["cer"],
        "diacritic_char_accuracy": m["diacritic_char_accuracy"] >= th["diacritic_char_accuracy"],
        "unicode_nfc_clean": u["is_nfc"] and u["replacement_chars"] == 0
                             and u["private_use_chars"] == 0 and u["control_chars"] == 0,
        "article_recall": m["structure"]["article_recall"] >= th["article_recall"],
    }
    m["checks"], m["passed"], m["thresholds"] = checks, all(checks.values()), th
    return m


def evaluate_noref(hyp_raw: str, expected_articles: int | None = None,
                   page_confs: list[float] | None = None) -> dict:
    """Đánh giá khi CHƯA có bản gold: Unicode + độ liên tục số 'Điều' + độ tin cậy OCR.
    Số 'Điều' bị thiếu/lệch trong dãy 1..N là dấu hiệu tiêu đề bị OCR hỏng."""
    text = unicodedata.normalize("NFC", hyp_raw)
    nums = [int(n) for n in re.findall(ARTICLE_RE, text)]
    found = set(nums)
    last = expected_articles or (max(found) if found else 0)
    missing = [n for n in range(1, last + 1) if n not in found]
    out = {"unicode": unicode_report(hyp_raw),
           "articles_found": len(found), "articles_expected": last,
           "missing_articles": missing,
           "duplicate_articles": sorted(n for n in found if nums.count(n) > 1),
           "article_recall": round(1 - len(missing) / last, 5) if last else 0.0,
           "khoan_lines": len(re.findall(r"(?m)^\s*\d+\.\s", text)),
           "diem_lines": len(re.findall(r"(?m)^\s*[a-zđ]\)\s", text)),
           "chuong": re.findall(r"(?m)^\s*Chương\s+([IVXLC]+)", text)}
    if page_confs:
        out["mean_conf"] = round(sum(page_confs) / len(page_confs), 2)
        out["min_conf_page"] = round(min(page_confs), 2)
    u = out["unicode"]
    out["unicode_clean"] = (u["is_nfc"] and u["replacement_chars"] == 0
                            and u["private_use_chars"] == 0 and u["control_chars"] == 0)
    return out


def find_hyp(hyp_dir: Path, stem: str) -> Path | None:
    for p in (hyp_dir / stem / f"{stem}.txt", hyp_dir / f"{stem}.txt"):
        if p.exists():
            return p
    return None


def to_markdown(results: dict[str, dict]) -> str:
    pct = lambda x: f"{x * 100:.2f}%"
    ok = lambda b: "✅" if b else "❌"
    rows = ["# Báo cáo đánh giá OCR tiếng Việt", "",
            "| Văn bản | CER | WER | CER không dấu | Ký tự có dấu đúng | Lỗi chỉ sai dấu | "
            "NFC sạch | Điều tìm lại được | Đạt |", "|---|---|---|---|---|---|---|---|---|"]
    for name, m in results.items():
        rows.append(f"| {name} | {pct(m['cer'])} | {pct(m['wer'])} | {pct(m['base_cer_no_diacritics'])} "
                    f"| {pct(m['diacritic_char_accuracy'])} | {m['diacritic_only_errors']} "
                    f"| {ok(m['checks']['unicode_nfc_clean'])} | {pct(m['structure']['article_recall'])} "
                    f"| {ok(m['passed'])} |")
    th = next(iter(results.values()))["thresholds"] if results else DEFAULT_THRESHOLDS
    rows += ["", "**Ngưỡng đạt (đề xuất):** "
             f"CER ≤ {pct(th['cer'])}; ký tự có dấu đúng ≥ {pct(th['diacritic_char_accuracy'])}; "
             f"Điều tìm lại được ≥ {pct(th['article_recall'])}; Unicode NFC, không có ký tự lỗi (U+FFFD).",
             "", "- *CER không dấu* tách riêng lỗi nhận sai chữ cái gốc khỏi lỗi sai dấu thanh/mũ.",
             "- *Lỗi chỉ sai dấu*: ký tự đúng chữ gốc nhưng sai dấu (vd. `ế` → `ê`)."]
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Đánh giá OCR tiếng Việt")
    ap.add_argument("--ref"), ap.add_argument("--hyp")
    ap.add_argument("--ref-dir"), ap.add_argument("--hyp-dir")
    ap.add_argument("--report", help="ghi báo cáo Markdown")
    ap.add_argument("--json", help="ghi kết quả JSON")
    ap.add_argument("--max-cer", type=float, default=DEFAULT_THRESHOLDS["cer"])
    ap.add_argument("--min-diacritic", type=float, default=DEFAULT_THRESHOLDS["diacritic_char_accuracy"])
    ap.add_argument("--min-article-recall", type=float, default=DEFAULT_THRESHOLDS["article_recall"])
    a = ap.parse_args(argv)
    th = {"cer": a.max_cer, "diacritic_char_accuracy": a.min_diacritic,
          "article_recall": a.min_article_recall}
    pairs: dict[str, tuple[Path, Path]] = {}
    if a.ref and a.hyp:
        pairs[Path(a.hyp).stem] = (Path(a.ref), Path(a.hyp))
    elif a.ref_dir and a.hyp_dir:
        for ref in sorted(Path(a.ref_dir).glob("*.txt")):
            hyp = find_hyp(Path(a.hyp_dir), ref.stem)
            if hyp:
                pairs[ref.stem] = (ref, hyp)
            else:
                print(f"Thiếu kết quả OCR cho {ref.stem}", file=sys.stderr)
    else:
        ap.error("cần --ref/--hyp hoặc --ref-dir/--hyp-dir")
    results = {n: evaluate(r.read_text("utf-8"), h.read_text("utf-8"), th)
               for n, (r, h) in pairs.items()}
    md = to_markdown(results)
    print(md)
    if a.report:
        Path(a.report).write_text(md, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if results and all(m["passed"] for m in results.values()) else 2


if __name__ == "__main__":
    sys.exit(main())
