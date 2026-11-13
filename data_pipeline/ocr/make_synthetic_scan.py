#!/usr/bin/env python3
"""Sinh PDF 'scan giả' tiếng Việt kèm ground truth để kiểm thử pipeline OCR.

Văn bản mẫu là NỘI DUNG GIẢ LẬP (không phải điều luật thật). Dùng để kiểm tra pipeline
khi chưa có bản scan thật; KHÔNG thay thế việc đánh giá trên văn bản thật.
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SAMPLE = """\
#CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
#VĂN BẢN MẪU KIỂM THỬ OCR (NỘI DUNG GIẢ LẬP)
#Chương I
#QUY ĐỊNH CHUNG
@Điều 1. Phạm vi điều chỉnh
Văn bản này quy định về đối tượng chịu thuế, người nộp thuế, căn cứ tính thuế, thuế suất, khai thuế, nộp thuế và hoàn thuế đối với hàng hóa, dịch vụ sử dụng cho sản xuất, kinh doanh và tiêu dùng ở Việt Nam.
@Điều 2. Đối tượng áp dụng
1. Tổ chức, cá nhân sản xuất, kinh doanh hàng hóa, dịch vụ chịu thuế.
2. Tổ chức, cá nhân nhập khẩu hàng hóa, mua dịch vụ của tổ chức, cá nhân ở nước ngoài.
3. Cơ quan quản lý thuế, công chức quản lý thuế và các tổ chức, cá nhân khác có liên quan.
@Điều 3. Giải thích từ ngữ
Trong văn bản này, các từ ngữ dưới đây được hiểu như sau:
1. Doanh thu tính thuế là toàn bộ số tiền bán hàng hóa, cung ứng dịch vụ, bao gồm cả khoản phụ thu và phí thu thêm mà cơ sở kinh doanh được hưởng, chưa có thuế giá trị gia tăng.
2. Hóa đơn điện tử là hóa đơn có mã hoặc không có mã của cơ quan thuế, được khởi tạo, lập, gửi, nhận, lưu trữ và quản lý bằng phương tiện điện tử.
3. Các trường hợp sau đây không phải kê khai, tính nộp thuế:
a) Chuyển nhượng vốn, chuyển nhượng quyền sử dụng đất theo quy định của pháp luật;
b) Dịch vụ cấp tín dụng, kinh doanh chứng khoán và bảo hiểm nhân thọ;
c) Sản phẩm trồng trọt, chăn nuôi, thủy sản chưa chế biến thành sản phẩm khác;
đ) Hàng hóa, dịch vụ cung ứng cho mục đích viện trợ nhân đạo, thiên tai, dịch bệnh.
@Điều 4. Thuế suất
1. Mức thuế suất 0% áp dụng đối với hàng hóa, dịch vụ xuất khẩu, vận tải quốc tế.
2. Mức thuế suất 5% áp dụng đối với nước sạch phục vụ sản xuất và sinh hoạt, thiết bị y tế, giáo khoa.
3. Mức thuế suất 10% áp dụng đối với hàng hóa, dịch vụ không thuộc các trường hợp quy định tại khoản 1 và khoản 2 Điều này.
@Điều 5. Mức giảm trừ và thời hạn nộp hồ sơ
Mức giảm trừ gia cảnh đối với người nộp thuế là 11.000.000 đồng/tháng; đối với mỗi người phụ thuộc là 4.400.000 đồng/tháng. Hồ sơ khai thuế nộp chậm nhất vào ngày thứ 20 của tháng tiếp theo kể từ ngày phát sinh nghĩa vụ.
@Điều 6. Hiệu lực thi hành
Văn bản này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026. Các quy định trước đây trái với văn bản này đều hết hiệu lực kể từ ngày văn bản này có hiệu lực.
"""

PROFILES = {  # dpi, xoay (độ), nhiễu, mờ, chất lượng JPEG, hệ số thu nhỏ
    "clean": dict(angle=0.0, noise=0, blur=0.0, jpeg=95, scale=1.0, shade=0.0),
    "light": dict(angle=0.8, noise=10, blur=0.6, jpeg=60, scale=1.0, shade=0.10),
    "heavy": dict(angle=-1.6, noise=22, blur=1.0, jpeg=35, scale=0.75, shade=0.25),
}
W, H, M, DPI = 1654, 2339, 150, 200
F_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def layout() -> tuple[list[list[tuple[str, bool]]], str]:
    reg, bold = ImageFont.truetype(F_REG, 30), ImageFont.truetype(F_BOLD, 30)
    lines: list[tuple[str, bool]] = []
    for para in SAMPLE.splitlines():
        head = para[:1] in "#@"
        text = para[1:] if head else para
        font = bold if head else reg
        cur = ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if font.getlength(trial) > W - 2 * M and cur:
                lines.append((cur, head)); cur = word
            else:
                cur = trial
        lines.append((cur, head))
    per_page = (H - 2 * M) // 50
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)]
    return pages, "\n".join(t for t, _ in lines) + "\n"


def draw_page(lines, ) -> Image.Image:
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    reg, bold = ImageFont.truetype(F_REG, 30), ImageFont.truetype(F_BOLD, 30)
    for i, (text, head) in enumerate(lines):
        d.text((M, M + i * 50), text, font=bold if head else reg, fill=0)
    return img


def degrade(img: Image.Image, p: dict, rng: np.random.Generator) -> Image.Image:
    if p["angle"]:
        img = img.rotate(p["angle"], resample=Image.BICUBIC, fillcolor=255)
    if p["blur"]:
        img = img.filter(ImageFilter.GaussianBlur(p["blur"]))
    arr = np.asarray(img, dtype=np.float32)
    if p["shade"]:
        grad = np.linspace(1 - p["shade"], 1.0, arr.shape[1], dtype=np.float32)[None, :]
        arr = arr * grad
    if p["noise"]:
        arr = arr + rng.normal(0, p["noise"], arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if p["scale"] != 1.0:
        small = img.resize((int(W * p["scale"]), int(H * p["scale"])), Image.LANCZOS)
        img = small.resize((W, H), Image.BICUBIC)
    import io
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=p["jpeg"]); buf.seek(0)
    return Image.open(buf).convert("L")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="data/synthetic")
    a = ap.parse_args()
    out = Path(a.out); (out / "gold").mkdir(parents=True, exist_ok=True)
    pages, gold = layout()
    (out / "gold" / "sample_clean.txt").write_text(gold, encoding="utf-8")
    for name, prof in PROFILES.items():
        rng = np.random.default_rng(42)
        imgs = [degrade(draw_page(pg), prof, rng) for pg in pages]
        imgs[0].save(out / f"sample_{name}.pdf", save_all=True, append_images=imgs[1:],
                     resolution=DPI)
        (out / "gold" / f"sample_{name}.txt").write_text(gold, encoding="utf-8")
        print(f"đã tạo sample_{name}.pdf ({len(imgs)} trang)")


if __name__ == "__main__":
    main()
