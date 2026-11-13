import unicodedata

from data_pipeline.ocr.evaluate_ocr import evaluate, strip_marks
from data_pipeline.ocr.ocr_pipeline import fix_foreign_latin, normalize_text

REF = "Điều 1. Phạm vi điều chỉnh\n1. Thuế suất 10%\nđ) hàng hóa xuất khẩu\n"


def test_normalize_to_nfc():
    nfd = unicodedata.normalize("NFD", "Điều chỉnh thuế")
    assert unicodedata.is_normalized("NFC", normalize_text(nfd))


def test_fix_foreign_latin():
    assert fix_foreign_latin("thiết bị ÿ tế")[0] == "thiết bị y tế"
    assert fix_foreign_latin("Phạm vi ế ộ ữ")[1] == 0  # chữ Việt giữ nguyên


def test_strip_marks_keeps_length():
    s = "Đường thuế ưu đãi"
    assert len(strip_marks(s)) == len(s) and strip_marks(s) == "Duong thue uu dai"


def test_perfect_passes():
    assert evaluate(REF, REF)["passed"]


def test_lost_diacritics_fail():
    r = evaluate(REF, "Dieu 1. Pham vi dieu chinh\n1. Thue suat 10%\nd) hang hoa xuat khau\n")
    assert not r["passed"] and r["diacritic_char_accuracy"] < 0.5


def test_nfd_output_flagged():
    r = evaluate(REF, unicodedata.normalize("NFD", REF))
    assert not r["checks"]["unicode_nfc_clean"]


def test_suspicious_thousands_separator():
    from data_pipeline.ocr.ocr_pipeline import suspicious_numbers
    assert suspicious_numbers("tối thiểu 6,000 tỷ đồng") == ["6,000"]   # 6.000 bị đọc thành 6,000
    assert suspicious_numbers("thuế suất 0,5% và 15,5 triệu đồng/tháng") == []  # thập phân hợp lệ
    assert suspicious_numbers("quy mô 12.000 tỷ đồng") == []


def test_colored_ink_detects_red_stamp():
    from PIL import Image, ImageDraw
    from data_pipeline.ocr.ocr_pipeline import STAMP_INK_PCT, colored_ink_pct
    plain = Image.new("RGB", (400, 400), "white")
    stamped = plain.copy()
    ImageDraw.Draw(stamped).ellipse((100, 100, 300, 300), outline=(200, 30, 30), width=12)
    assert colored_ink_pct(plain) <= STAMP_INK_PCT < colored_ink_pct(stamped)


def test_article_heading_tolerates_ocr_punctuation():
    from data_pipeline.ocr.evaluate_ocr import evaluate_noref
    txt = "Điều 1, Phạm vi điều chỉnh\nĐiều 2. Người nộp thuế\nĐiều 3: Thu nhập\nĐiều 2 của Luật này quy định\n"
    r = evaluate_noref(txt, expected_articles=3)
    assert r["articles_found"] == 3 and r["missing_articles"] == []
