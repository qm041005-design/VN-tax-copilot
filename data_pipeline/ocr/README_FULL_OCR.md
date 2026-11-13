# OCR đầy đủ + đánh giá chất lượng (SCRUM-8)

Bổ sung cho `pilot.py` (tải 10 văn bản, OCR trang đầu). Phần này OCR **toàn bộ trang**, gắn cờ trang
cần người xem lại và **đo chất lượng**. Kết quả & lỗi đã biết: `data_pipeline/evidence/ocr_full_report_2026-11-12.md`.

```bash
pip install -r data_pipeline/requirements.txt -r data_pipeline/ocr/requirements-eval.txt
# Cần Tesseract + gói 'vie' (như README.md). Windows: đặt TESSERACT_CMD và TESSDATA_PREFIX.
python -m data_pipeline.ocr.ocr_pipeline <thư-mục-pdf> -o data_pipeline/local_data/ocr   # mặc định 150 DPI
python -m data_pipeline.ocr.check_facts --ocr-dir data_pipeline/local_data/ocr           # số liệu trọng yếu
python -m data_pipeline.ocr.eval_gold_pages --ocr-dir data_pipeline/local_data/ocr       # CER/dấu theo trang
python -m pytest data_pipeline/ocr/tests -q
```

| Module | Việc |
|---|---|
| `ocr_pipeline.py` | PDF→ảnh→deskew/Otsu→Tesseract `vie`→NFC; `auto` dùng text layer thật, trang scan thì OCR |
| `evaluate_ocr.py` | CER/WER, CER không dấu, độ chính xác ký tự có dấu, kiểm tra NFC/U+FFFD, bảo toàn Điều/Khoản/Điểm |
| `eval_gold_pages.py` | so từng trang với `evidence/gold_pages/` (bản chuẩn **sơ bộ, cần người rà**) |
| `check_facts.py` | đối chiếu thuế suất/mức giảm trừ/mốc hiệu lực (`evidence/ocr_critical_facts.json`) |
| `make_scan_from_pdf.py`, `make_synthetic_scan.py` | tạo scan giả để đo khi chưa có bản chuẩn |

**Cờ `needs_review`** trong JSON từng trang: confidence thấp, có con dấu/chữ ký màu, số dạng `6,000`
(nghi `6.000`), hoặc trang cuối. Confidence cao **không** đồng nghĩa đúng (xem báo cáo, mục 4).
Kết quả OCR nên giữ trạng thái `pending_human_review` cho tới khi có người thẩm định.
