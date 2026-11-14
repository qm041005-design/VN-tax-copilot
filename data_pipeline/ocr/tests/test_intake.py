"""Test SCRUM-20: chọn trang đại diện, quy tắc chất lượng, lưu nguồn/hash, nạp kết quả đối chiếu thủ công."""
import csv
import hashlib
import json

import fitz
import pytest
from PIL import Image, ImageDraw

from data_pipeline.ocr.intake import (OPERATOR, annotate, apply_review, assess, has_table_scan, run,
                                      select_pages)

BODY = "Dieu 1. Pham vi dieu chinh cua van ban nay quy dinh ve nguoi nop thue va can cu tinh thue. " * 4


def make_pdf(path, pages):
    doc = fitz.open()
    for i in range(pages):
        pg = doc.new_page(width=595, height=842)
        pg.insert_textbox(fitz.Rect(50, 60, 545, 780), f"Trang {i + 1}. " + BODY, fontsize=10)
    doc.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(tmp_path, pages=3, wrong_hash=False):
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    digest = make_pdf(pdf_dir / "DOC1.pdf", pages)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{
        "source_id": "DOC1", "legal_identifier": "01/2026/TEST", "official_url": "https://vanban.chinhphu.vn/x",
        "download_url": "https://datafiles.chinhphu.vn/x.pdf", "retrieved_at": "2026-11-12T00:00:00+00:00",
        "sha256": "0" * 64 if wrong_hash else digest}]), encoding="utf-8")
    return pdf_dir, manifest


def do_run(tmp_path, pdf_dir, manifest, **kw):
    kw.setdefault("min_pages", 20)
    out, ev = tmp_path / "out", tmp_path / "ev"
    out.mkdir(), ev.mkdir()
    summary = run(pdf_dir, manifest, out, ev, kw["min_pages"], kw.get("quota"), False, None)
    return summary, out, ev


# ---- chọn trang -------------------------------------------------------------
def test_select_pages_covers_table_scan_first_last_gold_and_quota():
    feats = [{"page": i, "scanned": True, "table": i == 8} for i in range(1, 16)]
    chosen = select_pages(feats, 7, forced=(4, 10))
    assert "trang_có_bảng" in chosen[8] and {1, 15, 4, 10} <= set(chosen) and len(chosen) >= 7
    assert chosen == select_pages(feats, 7, forced=(4, 10))      # xác định, tái lập được
    assert all("trang_scan" in chosen[p] for p in (1, 8))


def test_select_pages_small_documents():
    for n in (1, 2):
        feats = [{"page": i, "scanned": False, "table": False} for i in range(1, n + 1)]
        assert list(select_pages(feats, 7)) == list(range(1, n + 1))


# ---- quy tắc chất lượng ------------------------------------------------------
def ex(**kw):
    return {"text": "x" * 100, "conf": 95.0, "ink": 0.0, "error": None, "method": "tesseract_vie", **kw}


@pytest.mark.parametrize("kw,status", [
    ({}, "pending_human_review"),
    ({"conf": 75.0}, "pending_human_review"),
    ({"conf": 60.0}, "quarantined_low_confidence"),
    ({"text": "  "}, "quarantined_empty"),
    ({"text": "vốn tối thiểu 6,000 tỷ đồng " * 3}, "quarantined_suspect_numbers"),
    ({"ink": 0.4}, "quarantined_stamp_overlay"),
    ({"text": "abc \ufffd " * 10}, "quarantined_unicode"),
    ({"error": "RuntimeError: boom"}, "quarantined_error"),
])
def test_assess_status_rules(kw, status):
    assert assess(ex(**kw), table=False, last_page=False)[0] == status


def test_assess_flags():
    assert "confidence_70_80" in assess(ex(conf=75.0), table=False, last_page=False)[1]
    flags = assess(ex(), table=True, last_page=True)[1]
    assert "bảng_chưa_tái_dựng_cấu_trúc" in flags and "trang_cuối_chữ_ký" in flags


def test_table_detection_grid_vs_plain_text():
    grid = Image.new("L", (800, 1100), 255)
    d = ImageDraw.Draw(grid)
    for y in range(300, 700, 70):
        d.line([(100, y), (700, y)], fill=0, width=2)
    for x in range(100, 701, 150):
        d.line([(x, 300), (x, 650)], fill=0, width=2)
    assert has_table_scan(grid)
    plain = Image.new("L", (800, 1100), 255)
    ImageDraw.Draw(plain).line([(100, 100), (700, 100)], fill=0, width=2)   # chỉ một đường gạch chân
    assert not has_table_scan(plain)


# ---- lưu nguồn/hash/trang/phương pháp/trạng thái -----------------------------
def test_records_hold_provenance_hash_page_method_status(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=3)
    summary, out, ev = do_run(tmp_path, pdf_dir, manifest)
    recs = json.loads((ev / "ocr_intake_pages.json").read_text("utf-8"))
    assert [r["pdf_page"] for r in recs] == [1, 2, 3]             # số trang PDF đếm từ 1
    for r in recs:
        assert r["sha256_verified"] and r["pdf_sha256"] == r["pdf_sha256_manifest"]
        assert r["official_url"].startswith("https://") and r["legal_identifier"] == "01/2026/TEST"
        assert r["extraction_method"] == "native_pdf" and r["quality_status"] == "pending_human_review"
        assert r["processed_by"] == OPERATOR == "Nguyen Gia Quy"
        assert "text" not in r                                     # bản commit không chứa toàn văn
        text = (out / "pages" / f"DOC1_p{r['pdf_page']:03d}.txt").read_text("utf-8").rstrip("\n")
        assert r["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert summary["van_ban_thieu"] == [] and summary["trang_loi_can_xu_ly_lai"] == 0


def test_hash_mismatch_quarantines_every_page(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=3, wrong_hash=True)
    summary, _, ev = do_run(tmp_path, pdf_dir, manifest)
    recs = json.loads((ev / "ocr_intake_pages.json").read_text("utf-8"))
    assert {r["quality_status"] for r in recs} == {"quarantined_source_hash_mismatch"}
    assert not any(r["sha256_verified"] for r in recs) and summary["trang_loi_can_xu_ly_lai"] == 3
    queue = json.loads((ev / "ocr_intake_retry_queue.json").read_text("utf-8"))
    assert len(queue) == 3


def test_min_pages_quota_and_coverage_reporting(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=25)
    summary, _, _ = do_run(tmp_path, pdf_dir, manifest, min_pages=20)
    assert summary["tong_trang_da_xu_ly"] >= 20 and summary["dat_toi_thieu_trang"]
    assert summary["dat_du_10_van_ban"] is False                   # mới 1 văn bản: phải nói rõ là chưa đủ


# ---- đối chiếu thủ công ------------------------------------------------------
def test_apply_review_roundtrip(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=3)
    _, out, ev = do_run(tmp_path, pdf_dir, manifest)
    sheet = out / "ocr_intake_manual_review.csv"
    rows = list(csv.DictReader(open(sheet, encoding="utf-8-sig")))
    assert rows[0]["nguoi_doi_chieu"] == "Nguyen Gia Quy" and rows[0]["ket_qua"] == ""
    rows[0]["ket_qua"] = "ok"
    rows[1].update(ket_qua="loi", loai_loi="rơi_dấu_thanh", ghi_chu="thuế→thuê")
    with open(sheet, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader(), w.writerows(rows)
    summary = apply_review(out / "intake_pages.json", sheet, out, ev, manifest)
    st = {r["pdf_page"]: r["quality_status"] for r in json.loads((ev / "ocr_intake_pages.json").read_text("utf-8"))}
    assert st == {1: "verified_ok", 2: "rejected_manual", 3: "pending_human_review"}
    queue = json.loads((ev / "ocr_intake_retry_queue.json").read_text("utf-8"))
    assert [q["pdf_page"] for q in queue] == [2] and queue[0]["manual_notes"] == "thuế→thuê"
    assert summary["trang_loi_can_xu_ly_lai"] == 1


def test_apply_review_rejects_invalid_value(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=2)
    _, out, ev = do_run(tmp_path, pdf_dir, manifest)
    sheet = out / "ocr_intake_manual_review.csv"
    rows = list(csv.DictReader(open(sheet, encoding="utf-8-sig")))
    rows[0]["ket_qua"] = "tạm ổn"
    with open(sheet, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader(), w.writerows(rows)
    with pytest.raises(ValueError):
        apply_review(out / "intake_pages.json", sheet, out, ev, manifest)


def test_annotate_keeps_status_and_labels_note_as_ai_preliminary(tmp_path):
    pdf_dir, manifest = setup(tmp_path, pages=3)
    _, out, ev = do_run(tmp_path, pdf_dir, manifest)
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({"_ghi_chu": "bỏ qua", "DOC1:2": "đúng số liệu, sai dấu 1 chỗ"}), encoding="utf-8")
    annotate(out / "intake_pages.json", notes, out, ev, manifest)
    recs = {r["pdf_page"]: r for r in json.loads((ev / "ocr_intake_pages.json").read_text("utf-8"))}
    assert recs[2]["quality_status"] == "pending_human_review"          # nhận xét AI không đổi trạng thái
    assert "KHÔNG phải đối chiếu thủ công" in recs[2]["preliminary_check"]["by"]
    assert recs[2]["manual_review"]["result"] is None and "preliminary_check" not in recs[1]
    rows = list(csv.DictReader(open(ev / "ocr_intake_manual_review.csv", encoding="utf-8-sig")))
    assert rows[1]["nhan_xet_so_bo_AI"] == "đúng số liệu, sai dấu 1 chỗ" and rows[1]["ket_qua"] == ""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"DOC1:99": "x"}), encoding="utf-8")
    with pytest.raises(KeyError):
        annotate(out / "intake_pages.json", bad, out, ev, manifest)
