#!/usr/bin/env python3
"""Pipeline OCR tiếng Việt: PDF -> ảnh -> tiền xử lý -> OCR -> text chuẩn NFC + JSON.

Ví dụ:
    python -m data_pipeline.ocr.ocr_pipeline data/raw -o data/ocr --engine tesseract --dpi 150
    python -m data_pipeline.ocr.ocr_pipeline luat.pdf -o out --mode ocr --pages 1-5

Mỗi PDF sinh ra: <out>/<stem>/<stem>.txt, <stem>.json, page_001.txt, ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- #
# Chuẩn hoá Unicode
# --------------------------------------------------------------------------- #
STAMP_INK_PCT = 0.05  # % điểm ảnh màu đậm; trang thật có dấu đỏ: 0,11-0,84%, trang thường: 0%
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_text(text: str) -> str:
    """Đưa về NFC (chữ có dấu dựng sẵn), bỏ ký tự vô hình, gọn khoảng trắng."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_ZERO_WIDTH)
    text = _CONTROL.sub("", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_VI_LOWER = "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵđ"
VI_LETTERS = set(_VI_LOWER + _VI_LOWER.upper())


def fix_foreign_latin(text: str) -> tuple[str, int]:
    """Tesseract hay nhầm 'y' -> 'ÿ', 'i' -> 'ï'... (chữ Latin có dấu KHÔNG thuộc tiếng Việt).
    Bỏ dấu các ký tự đó về chữ cái gốc. Trả về (text, số ký tự đã sửa)."""
    out, n = [], 0
    for ch in text:
        if ch.isalpha() and ch not in VI_LETTERS and ord(ch) > 127:
            base = "".join(c for c in unicodedata.normalize("NFD", ch)
                           if unicodedata.category(c) != "Mn")
            if base.isascii() and base:
                out.append(base)
                n += 1
                continue
        out.append(ch)
    return "".join(out), n


_SUSPECT_NUM = re.compile(r"(?<![\d.,])\d{1,3},\d{3}(?!\d)")


def suspicious_numbers(text: str) -> list[str]:
    """Số dạng '6,000': trong văn bản Việt, dấu phẩy là thập phân, nghìn dùng dấu chấm ('6.000').
    OCR hay đọc nhầm dấu chấm thành phẩy, biến 6.000 tỷ thành 6 tỷ. Chỉ CẢNH BÁO, không tự sửa."""
    return _SUSPECT_NUM.findall(text)


def colored_ink_pct(img: Image.Image) -> float:
    """% điểm ảnh có màu đậm (con dấu đỏ/xanh, chữ ký mực màu) - nơi OCR thường mất chữ."""
    hsv = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2HSV)
    return round(100.0 * float(((hsv[..., 1] > 90) & (hsv[..., 2] > 60)).mean()), 4)


# --------------------------------------------------------------------------- #
# Tiền xử lý ảnh
# --------------------------------------------------------------------------- #
def estimate_skew(gray: np.ndarray, max_angle: float = 5.0, step: float = 0.25) -> float:
    """Ước lượng góc nghiêng bằng projection profile (ổn định giữa các bản OpenCV)."""
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    _, bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    center = (w // 2, h // 2)
    best_score, best_angle = -1.0, 0.0
    for angle in np.arange(-max_angle, max_angle + step, step):
        m = cv2.getRotationMatrix2D(center, float(angle), 1.0)
        rotated = cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_NEAREST)
        score = float(np.var(rotated.sum(axis=1, dtype=np.float64)))
        if score > best_score:
            best_score, best_angle = score, float(angle)
    return best_angle


def preprocess(img: Image.Image, deskew: bool = True, binarize: str = "otsu",
               denoise: bool = False) -> Image.Image:
    gray = np.array(img.convert("L"))
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=8)
    if deskew:
        angle = estimate_skew(gray)
        if abs(angle) >= 0.1:
            h, w = gray.shape
            m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            gray = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    if binarize == "otsu":
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif binarize == "adaptive":
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 41, 15)
    return Image.fromarray(gray)


# --------------------------------------------------------------------------- #
# Engine OCR
# --------------------------------------------------------------------------- #
class TesseractEngine:
    name = "tesseract"

    def __init__(self, lang: str = "vie", psm: int = 3, oem: int = 1,
                 tessdata: str | None = None):
        import pytesseract
        if os.environ.get("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
        self.pt = pytesseract
        self.lang = lang
        self.config = f"--oem {oem} --psm {psm}"
        if tessdata:
            os.environ["TESSDATA_PREFIX"] = tessdata

    def run(self, img: Image.Image) -> tuple[str, float]:
        d = self.pt.image_to_data(img, lang=self.lang, config=self.config,
                                  output_type=self.pt.Output.DICT)
        lines: dict[tuple, list[str]] = {}
        confs: list[float] = []
        for i, word in enumerate(d["text"]):
            if not word.strip():
                continue
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            lines.setdefault(key, []).append(word)
            c = float(d["conf"][i])
            if c >= 0:
                confs.append(c)
        out, prev = [], None
        for key in sorted(lines):
            if prev is not None and key[:2] != prev[:2]:
                out.append("")  # ngắt đoạn
            out.append(" ".join(lines[key]))
            prev = key
        return "\n".join(out), (sum(confs) / len(confs) if confs else 0.0)


class PaddleEngine:
    """Engine thử nghiệm: cần `pip install paddlepaddle paddleocr` và tải model lần đầu."""
    name = "paddleocr"

    def __init__(self, lang: str = "vi", **_):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(lang=lang)

    def run(self, img: Image.Image) -> tuple[str, float]:
        arr = np.array(img.convert("RGB"))
        boxes: list[tuple[float, float, float, str, float]] = []  # (yc, x, h, text, conf)
        if hasattr(self.ocr, "predict"):  # PaddleOCR >= 3
            for res in self.ocr.predict(arr):
                for poly, txt, sc in zip(res["rec_polys"], res["rec_texts"], res["rec_scores"]):
                    p = np.array(poly)
                    boxes.append((p[:, 1].mean(), p[:, 0].min(), np.ptp(p[:, 1]), txt, float(sc)))
        else:  # PaddleOCR 2.x
            for page in self.ocr.ocr(arr) or []:
                for poly, (txt, sc) in page or []:
                    p = np.array(poly)
                    boxes.append((p[:, 1].mean(), p[:, 0].min(), np.ptp(p[:, 1]), txt, float(sc)))
        if not boxes:
            return "", 0.0
        boxes.sort(key=lambda b: (b[0], b[1]))
        thr = 0.6 * float(np.median([b[2] for b in boxes]))
        lines, cur, cur_y = [], [], None
        for b in boxes:
            if cur_y is None or abs(b[0] - cur_y) <= thr:
                cur.append(b)
                cur_y = b[0] if cur_y is None else (cur_y + b[0]) / 2
            else:
                lines.append(cur)
                cur, cur_y = [b], b[0]
        lines.append(cur)
        text = "\n".join(" ".join(t[3] for t in sorted(l, key=lambda b: b[1])) for l in lines)
        return text, 100.0 * sum(b[4] for b in boxes) / len(boxes)


def make_engine(name: str, lang: str, tessdata: str | None, psm: int):
    if name == "tesseract":
        return TesseractEngine(lang=lang, psm=psm, tessdata=tessdata)
    if name == "paddle":
        return PaddleEngine(lang="vi")
    raise ValueError(f"Engine không hỗ trợ: {name}")


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _open(pdf: Path):
    import fitz  # PyMuPDF (đã có trong data_pipeline/requirements.txt)
    return fitz.open(str(pdf))


def pdf_page_count(pdf: Path) -> int:
    with _open(pdf) as doc:
        return len(doc)


def pdf_text_layer(pdf: Path, page: int) -> str:
    with _open(pdf) as doc:
        return doc[page - 1].get_text("text")


def is_scanned_page(pdf: Path, page: int, min_coverage: float = 0.5) -> bool:
    """True nếu ảnh phủ >= min_coverage diện tích trang (tức là bản scan).
    Cần thiết vì nhiều bản scan có lớp text lẻ (vd. chữ ký số) khiến 'có text layer'
    không đồng nghĩa 'có nội dung'. Logo/con dấu nhỏ không bị tính nhầm."""
    with _open(pdf) as doc:
        pg = doc[page - 1]
        area = abs(pg.rect.width * pg.rect.height) or 1.0
        covered = 0.0
        for info in pg.get_image_info():
            b = info["bbox"]
            covered = max(covered, max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1]))
        return covered / area >= min_coverage


def render_page(pdf: Path, page: int, dpi: int) -> Image.Image:
    with _open(pdf) as doc:
        pix = doc[page - 1].get_pixmap(dpi=dpi, colorspace="rgb", alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(1, total + 1))
    pages: set[int] = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return sorted(p for p in pages if 1 <= p <= total)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def process_pdf(pdf: Path, out_root: Path, engine, dpi: int = 150, mode: str = "auto",
                pages: str | None = None, min_conf: float = 80.0, min_text_layer: int = 80,
                deskew: bool = True, binarize: str = "otsu", denoise: bool = False,
                save_images: bool = False) -> dict:
    out_dir = out_root / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    total = pdf_page_count(pdf)
    results = []
    for p in parse_pages(pages, total):
        t0 = time.time()
        fixed = 0
        layer = normalize_text(pdf_text_layer(pdf, p)) if mode == "auto" else ""
        use_layer = (mode == "auto" and len(layer) >= min_text_layer
                     and not is_scanned_page(pdf, p))
        ink = 0.0
        if use_layer:
            text, conf, source = layer, 100.0, "text_layer"
        else:
            raw_img = render_page(pdf, p, dpi)
            ink = colored_ink_pct(raw_img)
            img = preprocess(raw_img, deskew, binarize, denoise)
            if save_images:
                img.save(out_dir / f"page_{p:03d}.png")
            raw, conf = engine.run(img)
            text, fixed = fix_foreign_latin(normalize_text(raw))
            source = engine.name
        sus = suspicious_numbers(text)
        reasons = []
        if conf < min_conf:
            reasons.append("confidence_thấp")
        if ink > STAMP_INK_PCT:
            reasons.append("có_con_dấu_hoặc_chữ_ký_màu")
        if sus:
            reasons.append("số_có_dấu_phẩy_nghìn_đáng_ngờ")
        if p == total and source != "text_layer":
            reasons.append("trang_cuối_(chữ_ký/con_dấu)")
        (out_dir / f"page_{p:03d}.txt").write_text(text + "\n", encoding="utf-8")
        results.append({"page": p, "source": source, "chars": len(text),
                        "foreign_chars_fixed": fixed,
                        "mean_conf": round(conf, 2), "color_ink_pct": ink,
                        "suspicious_numbers": sus, "review_reasons": reasons,
                        "needs_review": bool(reasons),
                        "seconds": round(time.time() - t0, 2), "text": text})
        print(f"  [{pdf.name}] trang {p}/{total}: {source}, conf={conf:.1f}"
              + (f"  ⚠ {','.join(reasons)}" if reasons else ""), file=sys.stderr)
    full = "\n\n".join(r["text"] for r in results)
    (out_dir / f"{pdf.stem}.txt").write_text(full + "\n", encoding="utf-8")
    meta = {"file": pdf.name, "sha256": sha256(pdf), "engine": engine.name, "dpi": dpi,
            "mode": mode, "unicode_form": "NFC", "total_pages": total,
            "processed_pages": len(results),
            "pages_need_review": [r["page"] for r in results if r["needs_review"]],
            "pages": results}
    (out_dir / f"{pdf.stem}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OCR PDF văn bản pháp luật tiếng Việt")
    ap.add_argument("inputs", nargs="+", help="file PDF hoặc thư mục chứa PDF")
    ap.add_argument("-o", "--out", default="data/ocr")
    ap.add_argument("--engine", choices=["tesseract", "paddle"], default="tesseract")
    ap.add_argument("--lang", default="vie", help="ngôn ngữ Tesseract (mặc định vie)")
    ap.add_argument("--tessdata", default=None, help="thư mục chứa vie.traineddata")
    ap.add_argument("--psm", type=int, default=3)
    ap.add_argument("--dpi", type=int, default=150,
                    help="mặc định 150: đo trên 4 trang scan thật, 300 DPI cho kết quả dấu kém hơn")
    ap.add_argument("--mode", choices=["auto", "ocr"], default="auto",
                    help="auto: dùng text layer nếu có; ocr: luôn OCR")
    ap.add_argument("--pages", default=None, help="vd: 1-5,8")
    ap.add_argument("--min-conf", type=float, default=80.0)
    ap.add_argument("--binarize", choices=["otsu", "adaptive", "none"], default="otsu")
    ap.add_argument("--no-deskew", action="store_true")
    ap.add_argument("--denoise", action="store_true")
    ap.add_argument("--save-images", action="store_true")
    a = ap.parse_args(argv)

    files: list[Path] = []
    for item in map(Path, a.inputs):
        files += sorted(item.glob("*.pdf")) if item.is_dir() else [item]
    if not files:
        print("Không tìm thấy file PDF nào.", file=sys.stderr)
        return 1
    engine = make_engine(a.engine, a.lang, a.tessdata, a.psm)
    for pdf in files:
        meta = process_pdf(pdf, Path(a.out), engine, a.dpi, a.mode, a.pages, a.min_conf,
                           deskew=not a.no_deskew, binarize=a.binarize,
                           denoise=a.denoise, save_images=a.save_images)
        print(f"{pdf.name}: {meta['processed_pages']} trang, "
              f"cần xem lại: {meta['pages_need_review'] or 'không'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
