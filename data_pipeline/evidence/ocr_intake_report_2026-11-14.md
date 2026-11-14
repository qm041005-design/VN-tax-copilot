# Báo cáo SCRUM-20 – Kiểm thử OCR và chuẩn hóa dữ liệu đầu vào (14/11/2026)

Người thực hiện: **Nguyen Gia Quy** · Nhánh: `feature/04-data-ocr-ingestion` · Hạn Jira: 15/11/2026

## 1. Đối chiếu 4 yêu cầu của ticket
| Yêu cầu | Tình trạng | Bằng chứng |
|---|---|---|
| Tiếp nhận module OCR đã có | **Xong** | Tiếp nhận `pilot.py`, `test_pilot.py`, manifest 10 văn bản (commit của Đặng Minh Quân, giữ nguyên tác giả); mở rộng bằng `ocr_pipeline.py`, `evaluate_ocr.py`, `intake.py` |
| ≥ 20 trang đại diện **từ 10 văn bản**, gồm trang scan và trang có bảng | **Chưa đạt đủ** | **35 trang** (32 scan, 9 có bảng) nhưng mới **8/10 văn bản**. Thiếu: ND123_2020, TT78_2014 (xem mục 4) |
| Lưu nguồn, mã băm, số trang, phương pháp, trạng thái chất lượng | **Xong** (cho 35 trang) | `ocr_intake_pages.json`; hash PDF khớp manifest 8/8 |
| Đối chiếu thủ công; tách trang lỗi để xử lý lại | **Một phần** | Đã tách 8 trang lỗi vào `ocr_intake_retry_queue.json` và thử xử lý lại (mục 3). Đối chiếu thủ công **của người chưa thực hiện**: có phiếu CSV + trang HTML; mới có nhận xét **sơ bộ của AI** cho 5 trang |

## 2. Kết quả 35 trang đại diện
Phương pháp: native_pdf 2, tesseract_vie 33.
Trạng thái tự động: pending_human_review: 27, quarantined_stamp_overlay: 5, quarantined_suspect_numbers: 1, quarantined_table_numbers: 2.
Số trang là số trang PDF đếm từ 1 (đúng quy ước `DATA_CONTRACT.md`), không phải số in trên giấy.

| Văn bản | Trang | Lý do chọn | Phương pháp | Conf | Hash PDF | Hash text | Trạng thái |
|---|---|---|---|---|---|---|---|
| TT219_2013 | 1/83 | trang scan, trang đầu | tesseract_vie | 91.9 | `4b0a41e0d3` ✓ | `2be9085a31` | pending_human_review |
| TT219_2013 | 42/83 | trang scan | tesseract_vie | 93.84 | `4b0a41e0d3` ✓ | `7d7345e407` | pending_human_review |
| TT219_2013 | 69/83 | trang có bảng | tesseract_vie | 87.27 | `4b0a41e0d3` ✓ | `8a9e159917` | quarantined_table_numbers |
| TT219_2013 | 83/83 | trang cuối | tesseract_vie | 93.36 | `4b0a41e0d3` ✓ | `2ba04eed66` | pending_human_review |
| TT111_2013 | 1/78 | trang scan, trang đầu | tesseract_vie | 87.87 | `7571311411` ✓ | `f3cc8f77ae` | pending_human_review |
| TT111_2013 | 21/78 | trang có bảng | tesseract_vie | 92.05 | `7571311411` ✓ | `9f5a01c140` | pending_human_review |
| TT111_2013 | 26/78 | trang có bảng | tesseract_vie | 93.17 | `7571311411` ✓ | `a723cc22fa` | pending_human_review |
| TT111_2013 | 40/78 | trang scan | tesseract_vie | 93.68 | `7571311411` ✓ | `97d54c4e12` | quarantined_suspect_numbers |
| TT111_2013 | 78/78 | trang cuối | tesseract_vie | 82.76 | `7571311411` ✓ | `49b50246ec` | pending_human_review |
| TT96_2015 | 1/38 | trang scan, trang đầu | tesseract_vie | 88.72 | `1138a97217` ✓ | `b38946a68a` | quarantined_stamp_overlay |
| TT96_2015 | 20/38 | trang scan | tesseract_vie | 93.42 | `1138a97217` ✓ | `30c141a9fc` | pending_human_review |
| TT96_2015 | 38/38 | trang cuối | tesseract_vie | 90.14 | `1138a97217` ✓ | `a5065cbd19` | pending_human_review |
| TT26_2015 | 1/43 | trang scan, trang đầu | tesseract_vie | 87.13 | `c82351a7f3` ✓ | `0570a2b520` | quarantined_stamp_overlay |
| TT26_2015 | 22/43 | trang scan | tesseract_vie | 93.26 | `c82351a7f3` ✓ | `d8f959b280` | pending_human_review |
| TT26_2015 | 36/43 | trang có bảng | tesseract_vie | 73.47 | `c82351a7f3` ✓ | `e7e6a77964` | quarantined_table_numbers |
| TT26_2015 | 37/43 | trang có bảng | tesseract_vie | 82.39 | `c82351a7f3` ✓ | `565ad2deab` | pending_human_review |
| TT26_2015 | 43/43 | trang cuối | tesseract_vie | 77.92 | `c82351a7f3` ✓ | `feadc02af9` | pending_human_review |
| LUAT48_2024 | 1/20 | trang đầu | native_pdf | - | `8be4caa345` ✓ | `5560fb0559` | pending_human_review |
| LUAT48_2024 | 2/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `37b6a57cbc` | pending_human_review |
| LUAT48_2024 | 20/20 | trang cuối | tesseract_vie | 92.56 | `8be4caa345` ✓ | `14c377e112` | pending_human_review |
| LUAT67_2025 | 1/21 | trang scan, trang đầu | tesseract_vie | 91.59 | `ae70646819` ✓ | `18839c13af` | quarantined_stamp_overlay |
| LUAT67_2025 | 10/21 | có bản chuẩn | tesseract_vie | 94.09 | `ae70646819` ✓ | `9c219a046d` | pending_human_review |
| LUAT67_2025 | 11/21 | trang scan | tesseract_vie | 94.54 | `ae70646819` ✓ | `60dc2428c9` | pending_human_review |
| LUAT67_2025 | 15/21 | có bản chuẩn | tesseract_vie | 94.25 | `ae70646819` ✓ | `bbb64d5f34` | pending_human_review |
| LUAT67_2025 | 21/21 | trang cuối | tesseract_vie | 93.21 | `ae70646819` ✓ | `f9ed16547d` | pending_human_review |
| LUAT109_2025 | 1/15 | trang scan, trang đầu | tesseract_vie | 92.6 | `b169757e90` ✓ | `38ba4ff809` | pending_human_review |
| LUAT109_2025 | 4/15 | có bản chuẩn | tesseract_vie | 94.88 | `b169757e90` ✓ | `86b92aaa60` | pending_human_review |
| LUAT109_2025 | 8/15 | trang có bảng, trang scan | tesseract_vie | 94.32 | `b169757e90` ✓ | `bd45c8cd06` | pending_human_review |
| LUAT109_2025 | 10/15 | có bản chuẩn | tesseract_vie | 94.64 | `b169757e90` ✓ | `8c5c98894e` | pending_human_review |
| LUAT109_2025 | 15/15 | trang cuối | tesseract_vie | 93.59 | `b169757e90` ✓ | `d19d7fac27` | quarantined_stamp_overlay |
| ND70_2025 | 1/74 | trang scan, trang đầu | tesseract_vie | 88.93 | `98abd34e95` ✓ | `103f3a662f` | quarantined_stamp_overlay |
| ND70_2025 | 38/74 | trang scan | tesseract_vie | 93.71 | `98abd34e95` ✓ | `ad4dcfe45e` | pending_human_review |
| ND70_2025 | 46/74 | trang có bảng | tesseract_vie | 90.0 | `98abd34e95` ✓ | `fcd232dd63` | pending_human_review |
| ND70_2025 | 47/74 | trang có bảng | tesseract_vie | 88.37 | `98abd34e95` ✓ | `0d3d13a673` | pending_human_review |
| ND70_2025 | 74/74 | trang cuối | tesseract_vie | 84.19 | `98abd34e95` ✓ | `1361eeff1e` | pending_human_review |

## 3. Trang lỗi đã tách (`ocr_intake_retry_queue.json`)
Mỗi trang lỗi được thử lại bằng bỏ mực màu và 200 DPI + adaptive; kết quả thử lại **không thay** kết quả gốc.
| Trang | Lỗi tự động phát hiện | Nhận xét sơ bộ (AI, chưa người xác nhận) |
|---|---|---|
| TT219_2013 tr.69 | `quarantined_table_numbers`: ô số trong bảng lẫn chữ (`3ô`, `s0`, `ø0`) | Bảng ví dụ GTGT: nhiều ô sai, mất dấu trừ (vd. `-20 -20` thành `50 20`). Không dùng số trong bảng; cần nhập lại |
| TT26_2015 tr.36 | `quarantined_table_numbers` | Biểu mẫu 01/GTGT: mã chỉ tiêu bị đọc sai (`[01]`→`Íð1]`), chưa dựng cột |
| TT111_2013 tr.40 | `quarantined_suspect_numbers`: `12,000` | Phải là `12.000.000` (dấu chấm; suy từ câu trước, chưa soi ảnh). Thử lại 200 DPI không còn số nghi, cần người xác nhận |
| TT96_2015 tr.1, TT26_2015 tr.1, ND70_2025 tr.1, LUAT67_2025 tr.1 | `quarantined_stamp_overlay`: dấu ký số/con dấu đè đầu trang | Chưa kiểm ảnh; trang đầu của LUAT67 đã biết lẫn rác từ dấu ký số |
| LUAT109_2025 tr.15 | `quarantined_stamp_overlay`: con dấu đè chữ ký | Chưa kiểm ảnh trong lần chạy này |

Quy tắc mới thêm trong lần này: trang **có bảng** mà có ≥ 5 ô số lẫn chữ thì bị cách ly (`quarantined_table_numbers`), vì trước đó trang số liệu sai vẫn được xếp `pending_human_review` với confidence 87%.

## 4. Văn bản còn thiếu so với 10 văn bản của manifest
- **ND123_2020 (123/2020/NĐ-CP, 123 trang)**: chỉ có tệp `.txt` rỗng (244 dòng trắng, không có chữ), không có PDF.
- **TT78_2014 (78/2014/TT-BTC, 76 trang)**: tệp đã gửi tên `TT-78.pdf` thực chất là **Thông tư 78/2021/TT-BTC** (31 trang, hướng dẫn hóa đơn, chứng từ), hash không khớp manifest. Cần PDF đúng của TT 78/2014 (https://datafiles.chinhphu.vn/cpp/files/vbpq/2014/07/tt-78.signed.pdf).
- 8 PDF còn lại có hash **khớp** manifest.

## 5. Giới hạn cần biết
- Lần chạy này dùng **bản thay thế tạm cho PyMuPDF dựa trên poppler** (môi trường không cài được PyMuPDF). Dựng ảnh khác nhau có thể cho kết quả OCR lệch nhẹ (vd. `6.000` ở LUAT67 tr.15 đọc đúng ngay lần này, nhưng lần chạy bằng PyMuPDF trước đó đọc `6,000`). Cần chạy lại bằng PyMuPDF thật trước khi nghiệm thu.
- 6/20 test trong `test_intake.py` (các test tự dựng PDF bằng PyMuPDF) **không chạy được** ở môi trường này; 14 test còn lại qua, kể cả 2 test mới cho quy tắc bảng.
- Chỉ 4 trang có bản chuẩn (gold) từ trước, do AI chép, chưa người rà; 7 văn bản mới chưa có bản chuẩn nên chưa đo CER.
- Trạng thái `pending_human_review` nghĩa là **chưa ai đối chiếu**, không phải "đạt". Cấu trúc bảng chưa được tái dựng ở cả 9 trang bảng.

## 6. Việc còn lại để hoàn thành SCRUM-20
```bash
# trên máy có PyMuPDF thật, đã có đủ PDF trong data_pipeline/local_data (đặt tên <source_id>.pdf)
python -m data_pipeline.ocr.intake run
# mở data_pipeline/local_data/intake/review/index.html, điền cột ket_qua (ok/loi), loai_loi, ghi_chu trong ocr_intake_manual_review.csv, rồi:
python -m data_pipeline.ocr.intake apply-review --csv data_pipeline/local_data/intake/ocr_intake_manual_review.csv
```
Cần bổ sung: PDF ND123_2020 và TT78_2014 đúng bản; chạy lại đủ 10 văn bản; người đối chiếu thủ công.
