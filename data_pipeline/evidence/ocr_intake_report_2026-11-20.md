# B?o c?o intake OCR (c?p nh?t sau apply-review)

## K?t qu? intake (t?ng quan)

- V?n b?n ?? x? l?: **10/10** (?? 10 v?n b?n, ??t t?i thi?u trang).
- T?ng trang ??i di?n ?? x? l?: **44** (scan: 40, native PDF: 4 trong ngu?n trang; ph??ng ph?p tr?ch xu?t: `tesseract_vie` 41, `native_pdf` 3).
- Trang c? c?/b?ng: **13**.
- Hash PDF kh?p manifest: **10/10**.
- Th?i ?i?m `apply-review`: **2026-11-21T12:38:32+00:00** (`nguoi_thuc_hien`: Nguyen Gia Quy).
- Ngu?n d? li?u chi ti?t: [data_pipeline/evidence/ocr_intake_pages.json](ocr_intake_pages.json), [data_pipeline/evidence/ocr_intake_retry_queue.json](ocr_intake_retry_queue.json), [data_pipeline/evidence/ocr_intake_summary.json](ocr_intake_summary.json), [data_pipeline/evidence/ocr_intake_manual_review.csv](ocr_intake_manual_review.csv).

> Ghi ch?: PDF, ?nh trang v? to?n v?n OCR n?m t?i `data_pipeline/local_data/intake/` (b? gitignore), kh?ng commit.

## K?t qu? ??i chi?u th? c?ng (?? ?p d?ng)

- S? d?ng review: **44/44** (?? ?i?n `nguoi_doi_chieu`, `ket_qua`, `loai_loi`, `ghi_chu`, `thoi_diem_doi_chieu`).
- K?t qu?: **`verified_ok`: 1**, **`rejected_manual`: 43**.
- Trang duy?t ??t (`ok`): **LUAT48_2024 trang 18**.
- C?c trang c?n l?i (`loi`) ?? ???c ??a v?o h?ng ??i x? l? l?i: **43 m?c** trong [ocr_intake_retry_queue.json](ocr_intake_retry_queue.json) (`trang_loi_can_xu_ly_lai: 43`, `next_action`: x? l? l?i ho?c g? tay r?i ??i chi?u).

### Ph?n b? theo v?n b?n

| V?n b?n | S? trang duy?t | OK | L?i |
|---|---:|---:|---:|
| LUAT109_2025 | 5 | 0 | 5 |
| LUAT48_2024 | 4 | 1 | 3 |
| LUAT67_2025 | 5 | 0 | 5 |
| ND123_2020 | 5 | 0 | 5 |
| ND70_2025 | 5 | 0 | 5 |
| TT111_2013 | 4 | 0 | 4 |
| TT219_2013 | 5 | 0 | 5 |
| TT26_2015 | 5 | 0 | 5 |
| TT78_2014 | 3 | 0 | 3 |
| TT96_2015 | 3 | 0 | 3 |

### Nh?n x?t l?i ch?nh (t?m t?t t? ??i chi?u ?nh/OCR)

- Sai/nh?m s? hi?u, ng?y th?ng, k? t? s? v? m? bi?u m?u (v? d? TT219, ND123, TT78, LUAT109, TT111).
- L?i ch?nh t?, d?u, t? v? k? t? OCR; nhi?u metadata k? s?/ch?n trang.
- D?u/ghi ch? c?ng v?n, con d?u ho?c ch? k? ch?ng l?n n?i dung (nhi?u trang ??u v? trang cu?i).
- M?t/b? c?u tr?c b?ng, bi?u m?u, c?ng th?c (TT111/TT26/LUAT48 v? c?c trang b?ng/bi?u).
- M?t s? trang PDF native g?n c? b?ng nh?ng th?c ch?t thi?n v? v?n b?n/c?ng th?c, c?n x?c nh?n l?i khi s? d?ng l?m b?ng ch?ng b?ng.

## C?ng vi?c c?n l?i ?? ho?n th?nh intake (SCRUM-29)

1. **X? l? l?i 43 trang `rejected_manual`** theo [ocr_intake_retry_queue.json](ocr_intake_retry_queue.json): ch?y l?i OCR/c?i thi?n ti?n x? l? ho?c g? tay hi?u ??nh theo ?nh, sau ?? ??i chi?u l?i.
2. **C?p nh?t k?t qu? review** trong [data_pipeline/local_data/intake/ocr_intake_manual_review.csv](../local_data/intake/ocr_intake_manual_review.csv) (ngu?n l?m vi?c) v? ch?y l?i `python -m data_pipeline.ocr.intake apply-review --csv data_pipeline\local_data\intake\ocr_intake_manual_review.csv` ?? ??ng b? evidence/summary/retry queue.
3. **X?c nh?n ti?u ch? nghi?m thu tr?n Jira (SCRUM-29)**: ??nh k?m/??i chi?u evidence, commit/PR li?n quan ([PR #20](https://github.com/qm041005-design/VN-tax-copilot/pull/20), nh?nh `feature/04-data-ocr-ingestion`), v? chuy?n tr?ng th?i ticket theo quy tr?nh c?a team (li?n k?t key trong commit/PR ch? h? tr? t? ??ng n?u integration/automation ???c b?t).

*B?o c?o n?y thay th? n?i dung b?o c?o intake tr??c ?? (b?n c? b? l?i m? h?a v? ch?a ph?n ?nh k?t qu? `apply-review`).*
