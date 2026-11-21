# Báo cáo intake OCR – 20/11/2026

## Kết quả chạy

Đã tải 10 PDF từ liên kết chính thức trong manifest vào `data_pipeline/local_data`.
SHA-256 của cả 10 tệp khớp manifest; tổng cộng 571 trang nguồn. Lượt intake dùng
PyMuPDF thật và Tesseract 5.5.4 với ngôn ngữ `vie`:

| Chỉ số | Kết quả |
|---|---:|
| Văn bản đã xử lý | 10/10 |
| Trang đại diện đã xử lý | 44 |
| Trang scan / không scan | 40 / 4 |
| Trang được gắn cờ là có bảng | 13 |
| Trích xuất Tesseract / PDF native | 41 / 3 |
| Hash PDF khớp manifest | 10/10 |
| `pending_human_review` | 34 |
| `quarantined_stamp_overlay` | 7 |
| `quarantined_low_confidence` | 2 |
| `quarantined_table_numbers` | 1 |

Chi tiết máy sinh được lưu trong `ocr_intake_pages.json`,
`ocr_intake_retry_queue.json`, `ocr_intake_summary.json` và
`ocr_intake_manual_review.csv`. Ảnh trang và HTML đối chiếu được tạo cục bộ tại
`data_pipeline/local_data/intake/review/`; PDF, ảnh và toàn văn OCR không được commit.

## Ghi chú xem ảnh sơ bộ

Đã so ảnh với OCR ở các trang bị cách ly và các trang được gắn cờ bảng. Đây là
nhận xét sơ bộ do Nguyen Gia Quy thực hiện,
- `TT219_2013` trang 68: một số ô số bị đọc sai rõ ràng (ví dụ `400` thành `40o`,
  số `10` thành ký tự gần giống chữ); không dùng số liệu OCR này.
- `TT26_2015` trang 36: biểu mẫu và mã chỉ tiêu bị OCR sai nhiều; giữ cách ly.
- `ND123_2020` trang 1: ảnh ghi `123/2020/NĐ-CP`, OCR đọc thành `723/2020/NĐ-CP`.
- Các trang đầu có dấu/ghi chú chồng lên nội dung (`TT96_2015` p.1,
  `TT26_2015` p.1, `ND123_2020` p.1, `TT78_2014` p.1, `LUAT67_2025` p.1,
  `ND70_2025` p.1) cần người xác nhận phần bị che. `LUAT109_2025` p.15 có
  dấu/chữ ký chồng lên vùng ký tên và cũng cần xác nhận.
- `TT111_2013` p.21/p.78 và các trang biểu mẫu/bảng khác cần soát riêng các
  cột và số liệu; OCR dạng văn bản không giữ được cấu trúc bảng.
- Một số trang PDF native được bộ dò gắn cờ bảng nhưng hình thể hiện chủ yếu là
  văn bản/công thức. Cần xác nhận cờ bảng trước khi dùng làm bằng chứng về bảng.

Nhận xét sơ bộ do Nguyen Gia Quy thực hiện đã được ghi cho 21 trang ưu tiên trong CSV; cột người đối chiếu được gán `Nguyen Gia Quy`. Đây chưa phải kết quả review của người: cả 44
dòng vẫn để trống `ket_qua` và thời điểm, chưa trang nào được xác nhận là
`verified_ok` hoặc `rejected_manual`. Người được phân công cần xem ảnh/OCR, cập
nhật `ket_qua` (`ok`/`loi`) và mô tả lỗi nếu có, rồi chạy `apply-review`.
Hệ thống ghi thời điểm UTC khi nạp kết quả và không cho xác nhận PDF sai hash
manifest.
