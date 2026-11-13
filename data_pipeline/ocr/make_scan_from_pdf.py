#!/usr/bin/env python3
"""Tạo bản 'scan giả' từ một PDF có text layer chuẩn, kèm gold = text layer.

Cho phép đo CER/độ chính xác dấu trên CHỮ LUẬT THẬT khi chưa có ai gõ tay bản chuẩn.
    python -m data_pipeline.ocr.make_scan_from_pdf luat48.pdf -o out --profile light --pages 1-6
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .make_synthetic_scan import PROFILES, degrade
from .ocr_pipeline import _open, normalize_text, render_page


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="data_pipeline/local_data/synth_from_real")
    ap.add_argument("--profile", choices=list(PROFILES), default="light")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pages", default=None, help="vd 1-6")
    a = ap.parse_args()
    pdf, out = Path(a.pdf), Path(a.out)
    (out / "gold").mkdir(parents=True, exist_ok=True)
    with _open(pdf) as doc:
        total = len(doc)
        first, last = (1, total)
        if a.pages:
            x, _, y = a.pages.partition("-")
            first, last = int(x), int(y or x)
        gold = normalize_text("\n".join(doc[i - 1].get_text("text") for i in range(first, last + 1)))
    rng = np.random.default_rng(7)
    prof, outs = PROFILES[a.profile], []
    for p in range(first, last + 1):
        gray = render_page(pdf, p, a.dpi).convert("L")
        w, h = gray.size
        outs.append(degrade(gray.resize((1654, 2339)), prof, rng).resize((w, h)))
    name = f"{pdf.stem}_{a.profile}"
    outs[0].save(out / f"{name}.pdf", save_all=True, append_images=outs[1:], resolution=a.dpi)
    (out / "gold" / f"{name}.txt").write_text(gold + "\n", encoding="utf-8")
    print(f"{name}: {len(outs)} trang, gold {len(gold)} ký tự")


if __name__ == "__main__":
    main()
