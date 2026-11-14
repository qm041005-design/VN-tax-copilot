"""Hồi quy: trang scan có text layer lẻ (chữ ký số) KHÔNG được coi là 'đã có text'.
Lỗi thật gặp trên Luật 67/2025/QH15 (bản scan Kodak + dấu ký số của Cổng TTĐT Chính phủ)."""
import shutil

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from data_pipeline.ocr.ocr_pipeline import TesseractEngine, is_scanned_page, process_pdf

def _has_vie() -> bool:
    if shutil.which("tesseract") is None:
        return False
    import pytesseract
    return "vie" in pytesseract.get_languages(config="")


pytestmark = pytest.mark.skipif(not _has_vie(), reason="cần Tesseract + gói ngôn ngữ 'vie' (đặt TESSDATA_PREFIX nếu cần)")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"


def _make(tmp_path):
    img = Image.new("L", (1654, 2339), 255)
    ImageDraw.Draw(img).text((150, 200), "Điều 1. Phạm vi điều chỉnh", font=ImageFont.truetype(FONT, 40), fill=0)
    png = tmp_path / "p.png"
    img.save(png)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, filename=str(png))
    page.insert_text((20, 20), "Nguoi ky: CONG THONG TIN DIEN TU CHINH PHU Email: x@chinhphu.vn Co quan: VAN PHONG", fontsize=5)
    pdf = tmp_path / "stamp.pdf"
    doc.save(str(pdf))
    return pdf


def test_stamp_layer_does_not_skip_ocr(tmp_path):
    pdf = _make(tmp_path)
    assert is_scanned_page(pdf, 1)
    meta = process_pdf(pdf, tmp_path / "out", TesseractEngine(), dpi=200, mode="auto")
    assert meta["pages"][0]["source"] == "tesseract"
    assert "Điều 1" in meta["pages"][0]["text"]


def test_text_pdf_with_small_logo_uses_text_layer(tmp_path):
    img = Image.new("RGB", (400, 200), "red")
    png = tmp_path / "logo.png"
    img.save(png)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(20, 20, 120, 70), filename=str(png))
    page.insert_text((72, 200), "Điều 1. Phạm vi điều chỉnh. " * 8, fontsize=11)
    pdf = tmp_path / "text.pdf"
    doc.save(str(pdf))
    assert not is_scanned_page(pdf, 1)
