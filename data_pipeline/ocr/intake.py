#!/usr/bin/env python3
"""SCRUM-20 – Kiểm thử OCR và chuẩn hóa dữ liệu đầu vào.

Tiếp nhận module OCR có sẵn (pilot.py + ocr_pipeline.py), chọn trang ĐẠI DIỆN từ các văn bản
(trang scan, trang có bảng, trang đầu/cuối), xử lý, và lưu cho từng trang:
nguồn, mã băm (PDF + văn bản), số trang (PDF, đếm từ 1), phương pháp trích xuất, trạng thái chất lượng.
Trang lỗi được TÁCH RIÊNG vào hàng đợi xử lý lại; kết quả đối chiếu thủ công được nạp lại bằng `apply-review`.

    python -m data_pipeline.ocr.intake run --pdf-dir data_pipeline/local_data
    python -m data_pipeline.ocr.intake apply-review --csv <file đã điền>

Trạng thái chất lượng (quality_status):
    pending_human_review   qua kiểm tra tự động, CHƯA ai đối chiếu
    verified_ok            người đã đối chiếu, đúng         (chỉ đặt bởi apply-review)
    rejected_manual        người đã đối chiếu, có lỗi        (chỉ đặt bởi apply-review)
    quarantined_*          tự động phát hiện lỗi -> hàng đợi xử lý lại
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .evaluate_ocr import evaluate, unicode_report
from .ocr_pipeline import (STAMP_INK_PCT, TesseractEngine, _open, colored_ink_pct, fix_foreign_latin,
                           is_scanned_page, normalize_text, pdf_page_count, pdf_text_layer, preprocess,
                           render_page, sha256, suspicious_numbers)

OPERATOR = "Nguyen Gia Quy"
EXPECTED_DOCS = 10
MIN_PAGES = 20
LOW_CONF_QUARANTINE = 70.0   # như pilot.py
LOW_CONF_FLAG = 80.0
OCR_DPI = 150
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "evidence"
GOLD_DIR = EVIDENCE / "gold_pages"
GOLD_SOURCE = {"luat-48-2024-qh15-gtgt": "LUAT48_2024", "luat-67-2025-qh15-tndn": "LUAT67_2025",
               "luat-109-2025-qh15-tncn": "LUAT109_2025"}


# --------------------------------------------------------------------------- #
# Nhận diện trang có bảng
# --------------------------------------------------------------------------- #
def table_lines(img: Image.Image) -> tuple[int, int]:
    """Đếm số đường kẻ ngang/dọc dài (cụm liên tiếp) trên ảnh trang."""
    g = np.array(img.convert("L"))
    h, w = g.shape
    bw = (g < 140).astype(np.uint8) * 255
    hz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 6, 30), 1)))
    vt = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 30, 25))))

    def runs(v: np.ndarray) -> int:
        v = v.astype(int)
        return int(((v[1:] - v[:-1]) == 1).sum() + v[0])

    return runs(hz.sum(axis=1) > 0.3 * w * 255), runs(vt.sum(axis=0) > 0.02 * h * 255)


def has_table_scan(img: Image.Image) -> bool:
    """Bảng = >=3 đường ngang VÀ >=3 đường dọc. Đo trên scan thật: trang bảng 6x5, trang thường <=1 ngang."""
    h, v = table_lines(img)
    return h >= 3 and v >= 3


def has_table_native(pdf: Path, page: int) -> bool:
    try:
        with _open(pdf) as doc:
            return any(t.row_count >= 2 and t.col_count >= 2 for t in doc[page - 1].find_tables().tables)
    except Exception:  # noqa: BLE001 - bản PyMuPDF cũ không có find_tables
        return False


def classify_pages(pdf: Path, total: int) -> list[dict]:
    feats = []
    for p in range(1, total + 1):
        scanned = is_scanned_page(pdf, p)
        table = has_table_scan(render_page(pdf, p, 100)) if scanned else has_table_native(pdf, p)
        feats.append({"page": p, "scanned": scanned, "table": table})
    return feats


# --------------------------------------------------------------------------- #
# Chọn trang đại diện (xác định, tái lập được)
# --------------------------------------------------------------------------- #
def select_pages(feats: list[dict], quota: int, forced: tuple[int, ...] = ()) -> dict[int, list[str]]:
    n = len(feats)
    chosen: dict[int, list[str]] = {}

    def add(p: int, why: str) -> None:
        if 1 <= p <= n:
            chosen.setdefault(p, [])
            if why not in chosen[p]:
                chosen[p].append(why)

    for p in [f["page"] for f in feats if f["table"]][:2]:
        add(p, "trang_có_bảng")
    scanned = [f["page"] for f in feats if f["scanned"]]
    if scanned:
        add(scanned[0], "trang_scan")
        add(scanned[len(scanned) // 2], "trang_scan")
    add(1, "trang_đầu")
    add(n, "trang_cuối")
    for p in forced:
        add(p, "có_bản_chuẩn")
    rest = [f["page"] for f in feats if f["page"] not in chosen]
    k = quota - len(chosen)
    if k > 0 and rest:
        for i in sorted({round(x) for x in np.linspace(0, len(rest) - 1, min(k, len(rest)))}):
            add(rest[i], "trang_thân_văn_bản")
    return dict(sorted(chosen.items()))


# --------------------------------------------------------------------------- #
# Trích xuất + đánh giá chất lượng
# --------------------------------------------------------------------------- #
def drop_color_ink(img: Image.Image, sat: int = 70) -> Image.Image:
    """Xoá mực màu (con dấu đỏ/xanh, chữ ký) thành trắng; chữ đen giữ nguyên."""
    a = np.array(img.convert("RGB"))
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    mask = (hsv[..., 1] > sat) & (hsv[..., 2] > 40)
    a[cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0] = 255
    return Image.fromarray(a)


def extract_page(pdf: Path, page: int, engine: TesseractEngine, dpi: int = OCR_DPI,
                 min_text_layer: int = 80) -> dict:
    """Lấy text một trang: dùng text layer thật nếu có, ngược lại OCR. Không ném lỗi: ghi vào `error`."""
    out = {"method": "native_pdf", "conf": None, "ink": 0.0, "text": "", "fixed": 0, "error": None}
    try:
        layer = normalize_text(pdf_text_layer(pdf, page))
        scanned = is_scanned_page(pdf, page)
        if len(layer) >= min_text_layer and not scanned and "\ufffd" not in layer:
            out["text"] = layer
        else:
            img = render_page(pdf, page, dpi)
            out["ink"] = colored_ink_pct(img)
            raw, conf = engine.run(preprocess(img))
            out["text"], out["fixed"] = fix_foreign_latin(normalize_text(raw))
            out["method"], out["conf"] = "tesseract_vie", round(conf, 2)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def assess(ex: dict, *, table: bool, last_page: bool) -> tuple[str, list[str]]:
    """Quy tắc chất lượng tự động -> (quality_status, cờ). Thứ tự ưu tiên: lỗi > rỗng > conf thấp > số > con dấu."""
    flags: list[str] = []
    text = ex["text"]
    if table:
        flags.append("bảng_chưa_tái_dựng_cấu_trúc")
    if last_page:
        flags.append("trang_cuối_chữ_ký")
    if ex["conf"] is not None and LOW_CONF_QUARANTINE <= ex["conf"] < LOW_CONF_FLAG:
        flags.append("confidence_70_80")
    if ex["error"]:
        return "quarantined_error", flags
    if len(text.strip()) < 20:
        return "quarantined_empty", flags
    if ex["conf"] is not None and ex["conf"] < LOW_CONF_QUARANTINE:
        return "quarantined_low_confidence", flags
    if "\ufffd" in text or not unicodedata.is_normalized("NFC", text):
        return "quarantined_unicode", flags
    if suspicious_numbers(text):
        return "quarantined_suspect_numbers", flags
    if ex["ink"] > STAMP_INK_PCT:
        return "quarantined_stamp_overlay", flags
    return "pending_human_review", flags


def _tokens(t: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", t))


def retry_page(pdf: Path, page: int, engine: TesseractEngine, primary_text: str, out_dir: Path, tag: str) -> list[dict]:
    """Xử lý lại trang lỗi bằng các chiến lược khác; KHÔNG thay kết quả gốc, chỉ ghi nhận để người xác nhận."""
    strategies = {
        "bo_muc_mau": lambda: preprocess(drop_color_ink(render_page(pdf, page, OCR_DPI)), True, "otsu"),
        "dpi200_adaptive": lambda: preprocess(render_page(pdf, page, 200), True, "adaptive"),
    }
    base = set(_tokens(primary_text))
    attempts = []
    for name, make in strategies.items():
        try:
            raw, conf = engine.run(make())
            text = fix_foreign_latin(normalize_text(raw))[0]
        except Exception as exc:  # noqa: BLE001
            attempts.append({"strategy": name, "error": str(exc)})
            continue
        seen, new = set(), []
        for tok in _tokens(text):
            if tok not in base and tok not in seen:
                seen.add(tok)
                new.append(tok)
        (out_dir / f"{tag}.retry_{name}.txt").write_text(text + "\n", encoding="utf-8")
        attempts.append({"strategy": name, "mean_ocr_confidence": round(conf, 2), "text_chars": len(text),
                         "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                         "suspicious_numbers": suspicious_numbers(text), "new_tokens_vs_primary": new[:12],
                         "hint": "có_chữ_mới_cần_người_xác_nhận" if len(new) >= 3 else "không_rõ_cải_thiện"})
    return attempts


# --------------------------------------------------------------------------- #
# Luồng chính
# --------------------------------------------------------------------------- #
def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gold_pages_for(sid: str) -> dict[int, Path]:
    out = {}
    for f in GOLD_DIR.glob("*_p*.txt") if GOLD_DIR.exists() else []:
        m = re.match(r"(.+)_p(\d+)$", f.stem)
        if m and GOLD_SOURCE.get(m.group(1)) == sid:
            out[int(m.group(2))] = f
    return out


def run(pdf_dir: Path, manifest_path: Path, out_dir: Path, evidence_dir: Path | None, min_pages: int,
        quota: int | None, do_retry: bool, only: list[str] | None) -> dict:
    manifest = {d["source_id"]: d for d in json.loads(manifest_path.read_text("utf-8"))}
    expected = list(manifest)
    present = [s for s in expected if (pdf_dir / f"{s}.pdf").exists() and (not only or s in only)]
    (out_dir / "pages").mkdir(parents=True, exist_ok=True)
    (out_dir / "quarantine").mkdir(exist_ok=True)
    (out_dir / "review" / "img").mkdir(parents=True, exist_ok=True)
    quota = quota or max(3, math.ceil(min_pages / max(len(present), 1)))
    engine = TesseractEngine()
    records: list[dict] = []
    for sid in present:
        pdf, man = pdf_dir / f"{sid}.pdf", manifest[sid]
        total, digest = pdf_page_count(pdf), sha256(pdf)
        verified = digest == man.get("sha256")
        feats = classify_pages(pdf, total)
        gold = gold_pages_for(sid)
        chosen = select_pages(feats, quota, tuple(gold))
        print(f"{sid}: {total} trang, hash {'KHỚP' if verified else 'KHÁC'} manifest, chọn {list(chosen)}", file=sys.stderr)
        for page, why in chosen.items():
            f = feats[page - 1]
            ex = extract_page(pdf, page, engine)
            status, flags = assess(ex, table=f["table"], last_page=page == total)
            if not verified:
                status = "quarantined_source_hash_mismatch"
            text = ex["text"]
            tag = f"{sid}_p{page:03d}"
            (out_dir / "pages" / f"{tag}.txt").write_text(text + "\n", encoding="utf-8")
            render_page(pdf, page, 100).save(out_dir / "review" / "img" / f"{tag}.png")
            rec = {
                "source_id": sid, "legal_identifier": man["legal_identifier"], "official_url": man["official_url"],
                "download_url": man.get("download_url"), "retrieved_at": man.get("retrieved_at"),
                "pdf_file": pdf.name, "pdf_sha256": digest, "pdf_sha256_manifest": man.get("sha256"),
                "sha256_verified": verified, "total_pages": total, "pdf_page": page,
                "selection_reasons": why, "page_features": {"scanned": f["scanned"], "table": f["table"],
                                                             "colored_ink_pct": ex["ink"]},
                "extraction_method": ex["method"],
                "ocr_config": ({"engine": "tesseract", "lang": "vie", "dpi": OCR_DPI, "binarize": "otsu",
                                "psm": 3} if ex["method"] != "native_pdf" else None),
                "mean_ocr_confidence": ex["conf"], "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text_chars": len(text), "suspicious_numbers": suspicious_numbers(text),
                "unicode": {k: v for k, v in unicode_report(text).items() if k != "top_foreign_chars"},
                "quality_status": status, "quality_flags": flags, "error": ex["error"],
                "processed_by": OPERATOR, "processed_at": now(),
                "manual_review": {"status": "pending", "assigned_to": OPERATOR, "result": None,
                                  "error_types": [], "notes": None, "reviewed_at": None},
                "retry": {"needed": status.startswith("quarantined"), "attempts": []}, "text": text,
            }
            if page in gold:
                g = evaluate(gold[page].read_text("utf-8"), text)
                rec["gold_check"] = {"gold_source": "bản chép sơ bộ do Claude, chưa người rà", "cer": g["cer"],
                                     "diacritic_char_accuracy": g["diacritic_char_accuracy"]}
            if do_retry and status.startswith("quarantined") and status not in (
                    "quarantined_source_hash_mismatch", "quarantined_error"):
                rec["retry"]["attempts"] = retry_page(pdf, page, engine, text, out_dir / "quarantine", tag)
            records.append(rec)
    return finalize(records, expected, present, quota, min_pages, out_dir, evidence_dir)


def summarize(records: list[dict], expected: list[str], present: list[str], min_pages: int) -> dict:
    by = lambda key: {k: sum(1 for r in records if key(r) == k) for k in sorted({key(r) for r in records})}
    docs_done = sorted({r["source_id"] for r in records})
    return {
        "tong_trang_da_xu_ly": len(records), "van_ban_da_xu_ly": len(docs_done),
        "van_ban_ky_vong": len(expected), "van_ban_thieu": [s for s in expected if s not in present],
        "dat_toi_thieu_trang": len(records) >= min_pages,
        "dat_du_10_van_ban": len(docs_done) >= EXPECTED_DOCS,
        "trang_scan": sum(r["page_features"]["scanned"] for r in records),
        "trang_co_bang": sum(r["page_features"]["table"] for r in records),
        "theo_phuong_phap": by(lambda r: r["extraction_method"]),
        "theo_trang_thai": by(lambda r: r["quality_status"]),
        "hash_pdf_khop_manifest": sum(1 for s in docs_done if all(r["sha256_verified"] for r in records if r["source_id"] == s)),
        "trang_loi_can_xu_ly_lai": sum(r["retry"]["needed"] for r in records),
    }


def csv_rows(records: list[dict]) -> list[dict]:
    rows = []
    for r in records:
        mr = r["manual_review"]
        rows.append({"source_id": r["source_id"], "pdf_page": r["pdf_page"],
                     "ly_do_chon": "; ".join(r["selection_reasons"]), "phuong_phap": r["extraction_method"],
                     "trang_thai_tu_dong": r["quality_status"], "co_bao": "; ".join(r["quality_flags"]),
                     "nhan_xet_so_bo_AI": (r.get("preliminary_check") or {}).get("note", ""),
                     "nguoi_doi_chieu": mr["assigned_to"], "ket_qua": mr["result"] or "",
                     "loai_loi": "; ".join(mr["error_types"]), "ghi_chu": mr["notes"] or ""})
    return rows


def write_outputs(records: list[dict], summary: dict, out_dir: Path, evidence_dir: Path | None) -> None:
    (out_dir / "intake_pages.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    retry = [{k: r[k] for k in ("source_id", "legal_identifier", "pdf_page", "quality_status", "quality_flags",
                                 "suspicious_numbers", "extraction_method", "mean_ocr_confidence")}
             | {"retry_attempts": r["retry"]["attempts"], "manual_notes": r["manual_review"]["notes"],
                "next_action": "xử lý lại hoặc gõ tay rồi đối chiếu"}
             for r in records if r["retry"]["needed"]]
    cleaned = [{k: v for k, v in r.items() if k != "text"} for r in records]
    for name, data in (("ocr_intake_pages.json", cleaned), ("ocr_intake_retry_queue.json", retry),
                       ("ocr_intake_summary.json", summary)):
        for d in filter(None, (out_dir, evidence_dir)):
            (d / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for d in filter(None, (out_dir, evidence_dir)):
        with open(d / "ocr_intake_manual_review.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(csv_rows(records)[0]) if records else ["source_id"])
            w.writeheader()
            w.writerows(csv_rows(records))
    write_review_html(records, out_dir)


def write_review_html(records: list[dict], out_dir: Path) -> None:
    """Trang HTML cục bộ: ảnh trang bên trái, text OCR bên phải, để đối chiếu thủ công bằng mắt."""
    parts = ["<meta charset='utf-8'><title>Đối chiếu OCR</title><style>body{font:14px sans-serif}"
             ".r{display:flex;gap:12px;border-top:2px solid #888;margin:16px 0}.r img{width:48%}"
             "pre{white-space:pre-wrap;width:48%;background:#f6f6f6;padding:6px}</style>"]
    for r in records:
        tag = f"{r['source_id']}_p{r['pdf_page']:03d}"
        retry = "".join(f"<h4>Thử lại: {html.escape(a['strategy'])} – chữ mới: "
                        f"{html.escape(', '.join(a.get('new_tokens_vs_primary', [])))}</h4>" for a in r["retry"]["attempts"])
        parts.append(f"<h3>{tag} – {html.escape(r['quality_status'])} – {html.escape('; '.join(r['quality_flags']))}</h3>{retry}"
                     f"<div class='r'><img src='img/{tag}.png'><pre>{html.escape(r['text'])}</pre></div>")
    (out_dir / "review" / "index.html").write_text("\n".join(parts), encoding="utf-8")


def finalize(records, expected, present, quota, min_pages, out_dir, evidence_dir) -> dict:
    summary = summarize(records, expected, present, min_pages) | {"trang_moi_van_ban": quota,
                                                                   "nguoi_thuc_hien": OPERATOR, "ngay": now()}
    write_outputs(records, summary, out_dir, evidence_dir)
    return summary


def apply_review(records_path: Path, csv_path: Path, out_dir: Path, evidence_dir: Path | None,
                 manifest_path: Path = EVIDENCE / "ocr_pilot_manifest.json") -> dict:
    """Nạp kết quả đối chiếu thủ công: ok -> verified_ok; loi -> rejected_manual + hàng đợi xử lý lại."""
    records = json.loads(records_path.read_text("utf-8"))
    idx = {(r["source_id"], int(r["pdf_page"])): r for r in records}
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            res = (row.get("ket_qua") or "").strip().lower()
            if not res:
                continue
            if res not in ("ok", "loi"):
                raise ValueError(f"ket_qua chỉ nhận 'ok' hoặc 'loi', gặp {res!r} ở {row['source_id']} p{row['pdf_page']}")
            r = idx[(row["source_id"], int(row["pdf_page"]))]
            r["manual_review"] |= {"status": "done", "result": res, "reviewed_at": now(),
                                   "error_types": [e.strip() for e in (row.get("loai_loi") or "").split(";") if e.strip()],
                                   "notes": row.get("ghi_chu") or None}
            r["quality_status"] = "verified_ok" if res == "ok" else "rejected_manual"
            r["retry"]["needed"] = res == "loi" or (r["retry"]["needed"] and res != "ok")
    expected = [d["source_id"] for d in json.loads(manifest_path.read_text("utf-8"))]
    present = sorted({r["source_id"] for r in records})
    return finalize(records, expected, present, 0, MIN_PAGES, out_dir, evidence_dir)


PRELIM_BY = "Claude (AI) - sơ bộ, KHÔNG phải đối chiếu thủ công của người"


def annotate(records_path: Path, notes_path: Path, out_dir: Path, evidence_dir: Path | None,
             manifest_path: Path = EVIDENCE / "ocr_pilot_manifest.json") -> dict:
    """Gắn nhận xét đối chiếu SƠ BỘ (khoá 'SOURCE_ID:trang') vào bản ghi. Không đổi quality_status."""
    records = json.loads(records_path.read_text("utf-8"))
    notes = {k: v for k, v in json.loads(notes_path.read_text("utf-8")).items() if not k.startswith("_")}
    idx = {f"{r['source_id']}:{r['pdf_page']}": r for r in records}
    unknown = sorted(set(notes) - set(idx))
    if unknown:
        raise KeyError(f"Không có trang nào ứng với: {unknown}")
    for key, note in notes.items():
        idx[key]["preliminary_check"] = {"by": PRELIM_BY, "note": note, "at": now()}
    expected = [d["source_id"] for d in json.loads(manifest_path.read_text("utf-8"))]
    present = sorted({r["source_id"] for r in records})
    return finalize(records, expected, present, 0, MIN_PAGES, out_dir, evidence_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="chọn trang đại diện, xử lý, lưu nguồn/hash/trạng thái")
    r.add_argument("--pdf-dir", type=Path, default=Path("data_pipeline/local_data"))
    r.add_argument("--manifest", type=Path, default=EVIDENCE / "ocr_pilot_manifest.json")
    r.add_argument("--out", type=Path, default=Path("data_pipeline/local_data/intake"))
    r.add_argument("--evidence", type=Path, default=EVIDENCE, help="nơi ghi bản KHÔNG chứa text để commit")
    r.add_argument("--min-pages", type=int, default=MIN_PAGES)
    r.add_argument("--quota", type=int, help="số trang mỗi văn bản (mặc định đủ để đạt --min-pages)")
    r.add_argument("--no-retry", action="store_true")
    r.add_argument("--only", nargs="*", help="chỉ xử lý các source_id này")
    v = sub.add_parser("apply-review", help="nạp kết quả đối chiếu thủ công từ CSV")
    v.add_argument("--csv", type=Path, required=True)
    v.add_argument("--out", type=Path, default=Path("data_pipeline/local_data/intake"))
    v.add_argument("--evidence", type=Path, default=EVIDENCE)
    n = sub.add_parser("annotate", help="gắn nhận xét đối chiếu sơ bộ (JSON: {'SID:trang': 'ghi chú'})")
    n.add_argument("--notes", type=Path, required=True)
    n.add_argument("--out", type=Path, default=Path("data_pipeline/local_data/intake"))
    n.add_argument("--evidence", type=Path, default=EVIDENCE)
    a = ap.parse_args(argv)
    if a.cmd == "annotate":
        s = annotate(a.out / "intake_pages.json", a.notes, a.out, a.evidence)
    elif a.cmd == "run":
        a.out.mkdir(parents=True, exist_ok=True)
        s = run(a.pdf_dir, a.manifest, a.out, a.evidence, a.min_pages, a.quota, not a.no_retry, a.only)
    else:
        s = apply_review(a.out / "intake_pages.json", a.csv, a.out, a.evidence)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
