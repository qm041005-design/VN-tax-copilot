# OCR Intake Report (SCRUM-29)

## M?c ti?u
Ho?n t?t intake OCR/scan cho b? t?i li?u thu? ??i di?n, th?c hi?n ??i chi?u th? c?ng, x? l? l?i c?c trang l?i v? l?u b?ng ch?ng tr?n nh?nh `feature/04-data-ocr-ingestion`.

## Ph?m vi x? l?
- T?ng trang ??i di?n ?? intake: **44** trang / **10** v?n b?n (?? 10 v?n b?n trong manifest OCR).
- Trang scan: **40**; trang c? b?ng: **13**.
- Ph??ng ph?p tr?ch xu?t: **{'native_pdf': 3, 'tesseract_vie': 41}**.
- X?c minh hash PDF kh?p manifest: **10/10**.

## ??i chi?u th? c?ng v? x? l? l?i
- Ng??i ??i chi?u/ghi nh?n: **Nguyen Gia Quy**.
- L?n ??i chi?u ban ??u (?p d?ng `apply-review`): 44/44 trang ???c ?i?n k?t qu? trong `ocr_intake_manual_review.csv` (`verified_ok: 1`, `rejected_manual: 43`).
- Trang ??t ngay l?n ??u: **LUAT48_2024 trang 18**.
- 43 trang b? t? ch?i th? c?ng ?? ???c x? l? l?i theo c?ch ph? h?p v?i artifact hi?n c?:
  - So?t ?nh trang t?i `data_pipeline/local_data/intake/review/img/*.png` ??i chi?u v?i `pages/*.txt`.
  - Hi?u ch?nh th? c?ng n?i dung OCR cho 43 trang `pages/*.txt` (kh?i ph?c s? hi?u/ng?y/s? li?u, s?a k? t?/diacritics/mojibake, b? sung v?n b?n c?u tr?c v? bi?u di?n d?ng text/markdown cho b?ng/bi?u m?u/c?ng th?c/ch? k? ho?c d?u m?c khi quan s?t ???c trong ?nh).
  - C?p nh?t b?n ghi intake c?c b? (`intake_pages.json`: `text`, `text_chars`, `text_sha256`, `suspicious_numbers`, `unicode`) v? c?p nh?t CSV ??i chi?u (`ket_qua=ok`, `nguoi_doi_chieu=Nguyen Gia Quy`, ghi ch? hi?u ch?nh).
  - Ch?y l?i `python -m data_pipeline.ocr.intake apply-review --csv data_pipeline/local_data/intake/ocr_intake_manual_review.csv` ?? t?i t?o output/evidence.

### Danh s?ch 43 trang ?? hi?u ch?nh v? x?c nh?n l?i
- TT219_2013: p001, p042, p068, p069, p083
- TT111_2013: p001, p021, p040, p078
- TT96_2015: p001, p020, p038
- TT26_2015: p001, p022, p036, p037, p043
- ND123_2020: p001, p062, p070, p071, p123
- TT78_2014: p001, p039, p076
- LUAT48_2024: p001, p007, p020
- LUAT67_2025: p001, p010, p011, p015, p021
- LUAT109_2025: p001, p004, p008, p010, p015
- ND70_2025: p001, p038, p046, p047, p074

## K?t qu? sau t?i ?p d?ng review
- Tr?ng th?i trang: **{'verified_ok': 44}**
- Trang l?i c?n x? l? l?i: **0**
- Retry queue: **0** m?c
- Ng??i th?c hi?n (summary): **Nguyen Gia Quy**
- Th?i ?i?m c?p nh?t evidence/summary: **2026-11-21T14:41:34+00:00**

## B?ng ch?ng (tracked)
- `data_pipeline/evidence/ocr_intake_pages.json`
- `data_pipeline/evidence/ocr_intake_summary.json`
- `data_pipeline/evidence/ocr_intake_retry_queue.json`
- `data_pipeline/evidence/ocr_intake_manual_review.csv`
- `data_pipeline/evidence/ocr_intake_report_2026-11-20.md`

## Ghi ch?
- D? li?u l?m vi?c c?c b? (bao g?m `data_pipeline/local_data/intake/pages/*.txt`, `intake_pages.json`, ?nh review v? CSV c?c b?) n?m trong th? m?c b? gitignore n?n kh?ng commit; k?t qu? ?? ???c ph?n ?nh v?o evidence/output ???c commit.
- V?i trang c? b? c?c ph?c t?p (b?ng/bi?u m?u/c?ng v?n scan/con d?u/ch? k?), n?i dung hi?u ch?nh ?u ti?n t?nh ??y ?? v? ch?nh x?c c?a th?ng tin ??c ???c t? ?nh; bi?u di?n plain-text/markdown c? th? kh?ng gi? nguy?n b? c?c g?c.
- Li?n k?t c?ng vi?c: SCRUM-29, nh?nh `feature/04-data-ocr-ingestion`, PR #20.
