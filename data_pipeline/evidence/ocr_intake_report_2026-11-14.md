# Báo cáo SCRUM-20 – Kiểm thử OCR và chuẩn hóa dữ liệu đầu vào (14/11/2026)

Người thực hiện: **Nguyen Gia Quy** · Nhánh: `feature/04-data-ocr-ingestion` · Hạn Jira: 15/11/2026

## 1. Đối chiếu 4 yêu cầu của ticket
| Yêu cầu | Tình trạng | Bằng chứng |
|---|---|---|
| Tiếp nhận module OCR đã có | **Xong** | Tiếp nhận `pilot.py`, `test_pilot.py`, manifest 10 văn bản (commit `78df34d` của Đặng Minh Quân, giữ nguyên tác giả); mở rộng bằng `ocr_pipeline.py`, `evaluate_ocr.py`, `intake.py` |
| ≥ 20 trang đại diện **từ 10 văn bản**, gồm trang scan và trang có bảng | **Chưa đạt đủ** | 21 trang (14 scan, 1 có bảng) nhưng mới **3/10 văn bản**. Thiếu: TT219_2013, TT111_2013, TT96_2015, TT26_2015, ND123_2020, TT78_2014, ND70_2025 (chưa có file PDF) |
| Lưu nguồn, mã băm, số trang, phương pháp, trạng thái chất lượng | **Xong** (cho 21 trang) | `ocr_intake_pages.json`; hash PDF khớp manifest 3/3 |
| Đối chiếu thủ công; tách trang lỗi để xử lý lại | **Một phần** | Đã tách 3 trang lỗi và thử xử lý lại (mục 3). Đối chiếu thủ công **của người chưa thực hiện**: có phiếu CSV + trang HTML; mới có nhận xét **sơ bộ của AI** cho 5 trang |

## 2. Kết quả 21 trang đại diện
Phương pháp: native_pdf 6, tesseract_vie 15. Trạng thái tự động: pending_human_review: 18; quarantined_stamp_overlay: 2; quarantined_suspect_numbers: 1.
Số trang là số trang PDF đếm từ 1 (đúng quy ước `DATA_CONTRACT.md`), không phải số in trên giấy.

| Văn bản | Trang | Lý do chọn | Phương pháp | Conf | Hash PDF | Hash text | Trạng thái | Đo trên bản chuẩn sơ bộ |
|---|---|---|---|---|---|---|---|---|
| LUAT48_2024 | 1/20 | trang đầu | native_pdf | - | `8be4caa345` ✓ | `a8389d3a20` | pending_human_review | - |
| LUAT48_2024 | 2/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `a420ffff7f` | pending_human_review | - |
| LUAT48_2024 | 6/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `1266657394` | pending_human_review | - |
| LUAT48_2024 | 10/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `375999a48c` | pending_human_review | - |
| LUAT48_2024 | 15/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `268a0bb6cf` | pending_human_review | - |
| LUAT48_2024 | 19/20 | trang thân văn bản | native_pdf | - | `8be4caa345` ✓ | `9c2b988af7` | pending_human_review | - |
| LUAT48_2024 | 20/20 | trang cuối | tesseract_vie | 89.9 | `8be4caa345` ✓ | `0fa16d02aa` | pending_human_review | - |
| LUAT67_2025 | 1/21 | trang scan, trang đầu | tesseract_vie | 92.7 | `ae70646819` ✓ | `66ab0ced95` | quarantined_stamp_overlay | - |
| LUAT67_2025 | 2/21 | trang thân văn bản | tesseract_vie | 93.8 | `ae70646819` ✓ | `ce4fc8029e` | pending_human_review | - |
| LUAT67_2025 | 10/21 | có bản chuẩn | tesseract_vie | 94.9 | `ae70646819` ✓ | `9be73768a8` | pending_human_review | CER 0,35% / dấu 99,8% |
| LUAT67_2025 | 11/21 | trang scan | tesseract_vie | 94.6 | `ae70646819` ✓ | `c149139368` | pending_human_review | - |
| LUAT67_2025 | 15/21 | có bản chuẩn | tesseract_vie | 94.9 | `ae70646819` ✓ | `9a02aebae0` | quarantined_suspect_numbers | CER 0,31% / dấu 99,2% |
| LUAT67_2025 | 20/21 | trang thân văn bản | tesseract_vie | 94.9 | `ae70646819` ✓ | `2ab74fae20` | pending_human_review | - |
| LUAT67_2025 | 21/21 | trang cuối | tesseract_vie | 94.5 | `ae70646819` ✓ | `a1d5c9ef79` | pending_human_review | - |
| LUAT109_2025 | 1/15 | trang scan, trang đầu | tesseract_vie | 94.5 | `b169757e90` ✓ | `e3702b31b0` | pending_human_review | - |
| LUAT109_2025 | 2/15 | trang thân văn bản | tesseract_vie | 94.8 | `b169757e90` ✓ | `119ee16cbb` | pending_human_review | - |
| LUAT109_2025 | 4/15 | có bản chuẩn | tesseract_vie | 95.1 | `b169757e90` ✓ | `4d8ff40037` | pending_human_review | CER 0,44% / dấu 98,9% |
| LUAT109_2025 | 8/15 | trang có bảng, trang scan | tesseract_vie | 95.1 | `b169757e90` ✓ | `6d372ebb7d` | pending_human_review | - |
| LUAT109_2025 | 10/15 | có bản chuẩn | tesseract_vie | 95.1 | `b169757e90` ✓ | `451f0b9356` | pending_human_review | CER 1,24% / dấu 95,9% |
| LUAT109_2025 | 14/15 | trang thân văn bản | tesseract_vie | 94.9 | `b169757e90` ✓ | `088e1cf6ce` | pending_human_review | - |
| LUAT109_2025 | 15/15 | trang cuối | tesseract_vie | 94.4 | `b169757e90` ✓ | `3f66daf878` | quarantined_stamp_overlay | - |

## 3. Trang lỗi đã tách (`ocr_intake_retry_queue.json`) và kết quả xử lý lại
| Trang | Lỗi tự động phát hiện | Xử lý lại | Kết quả (cần người xác nhận) |
|---|---|---|---|
| LUAT67_2025 tr.15 | `6,000` (nghi `6.000`, dễ hiểu thành 6 tỷ) | 200 DPI + adaptive | **Đã đọc đúng `6.000 tỷ đồng`** (khớp ảnh) |
| LUAT109_2025 tr.15 | Con dấu đè lên chữ ký | bỏ mực màu; 200 DPI + adaptive | Khôi phục "Trần Thanh Mẫn" và "CHỦ TỊCH"; còn lỗi `QUÓC`, `Mam` |
| LUAT67_2025 tr.1 | Con dấu/dấu ký số ở đầu trang | bỏ mực màu; 200 DPI + adaptive | **Không cải thiện** – rác từ dấu ký số lẫn vào đầu trang; đề xuất cắt vùng đầu trang rồi OCR |

Chưa tự động: hai trang cuối có con dấu đen/xám (LUAT67 tr.21) không bị bắt bởi bộ dò mực màu; chỉ được gắn cờ "trang cuối chữ ký".

## 4. Trang có bảng
LUAT109_2025 tr.8 (biểu thuế luỹ tiến, Điều 9): đối chiếu ảnh (sơ bộ, do AI), **đủ 5 hàng, 20 giá trị số đều đúng**. Lỗi chữ ở tiêu đề cột/đoạn kế bên
(`luỹ tiến→luỹ tiền`, `triệu→ưiệu`, `phủ→phú`). **Cấu trúc cột chưa được tái dựng**: text nối theo dòng, nên cần bước dựng bảng riêng
trước khi dùng cho truy vấn theo ô. Văn bản có bảng trong 7 tài liệu còn lại (thông tư, nghị định có biểu mẫu) chưa được kiểm tra.

## 5. Giới hạn cần biết
- Mẫu chỉ 3/10 văn bản, nên **kết quả chưa đại diện cho thông tư/nghị định cũ** (2013–2015), vốn có thể là bản scan chất lượng thấp hơn và nhiều bảng hơn.
- "Bản chuẩn" để đo CER là bản chép sơ bộ do Claude, chưa người rà. Chỉ 4 trang có bản chuẩn.
- Trạng thái `pending_human_review` nghĩa là **chưa ai đối chiếu**, không phải "đạt".

## 6. Việc còn lại để hoàn thành SCRUM-20
```bash
python -m data_pipeline.ocr.pilot --max-pages 1      # tải đủ 10 PDF vào data_pipeline/local_data
python -m data_pipeline.ocr.intake run               # xử lý ≥ 20 trang từ 10 văn bản, ghi evidence
# mở data_pipeline/local_data/intake/review/index.html để đối chiếu ảnh với text;
# điền cột ket_qua (ok/loi), loai_loi, ghi_chu trong ocr_intake_manual_review.csv, rồi:
python -m data_pipeline.ocr.intake apply-review --csv data_pipeline/local_data/intake/ocr_intake_manual_review.csv
```
Quy ước trạng thái: `pending_human_review` → (`verified_ok` | `rejected_manual`); `quarantined_*` = lỗi tự động, nằm trong hàng đợi xử lý lại.
