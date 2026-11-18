# Bộ câu hỏi seed SCRUM-1

Phiên bản cập nhật ngày 11/11/2026. Dùng để phát triển pipeline và kiểm tra thủ công ban đầu, không phải bộ holdout hay kết quả nghiệm thu. Tất cả kết luận là nhãn dự thảo chờ chuyên gia thuế thẩm định.

| Nhóm | Trả lời được | Cần làm rõ | Tổng |
| :--- | ---: | ---: | ---: |
| VAT | 7 | 3 | 10 |
| CIT | 7 | 1 | 8 |
| PIT | 7 | 1 | 8 |
| EINVOICE | 3 | 1 | 4 |
| Tổng | 24 | 6 | 30 |

Giữ nguyên 16 ID cũ để thuận tiện đối chiếu Git. Sửa căn cứ của các câu năm 2024 vốn dẫn nhầm luật ban hành sau kỳ áp dụng. Thêm 14 câu về ngưỡng thanh toán, cộng gộp hóa đơn cùng ngày, chi phí TNDN, cư trú, thu nhập miễn thuế, thời điểm hóa đơn và thiếu dữ kiện.

## Cách sử dụng

Từ gốc repo chạy:

```powershell
python evaluation/validate_seed_dataset.py
```

Không cần thư viện ngoài Python standard library. Script trả mã lỗi 1 khi sai cấu trúc, trùng ID/câu hỏi, thiếu căn cứ cho câu trả lời được, thiếu câu hỏi làm rõ, sai miền nguồn hoặc dùng văn bản ban hành sau năm 2024 trong seed lịch sử. Kiểm tra năm ban hành chỉ là hàng rào cho bộ seed này, không phải bộ máy xác định hiệu lực hoặc hồi tố tổng quát. Script không gọi mạng, không đo Recall@10 và không chứng nhận tính đúng pháp lý.

`tax_period` là kỳ áp dụng; `research_as_of` là ngày nghiên cứu. `last_checked_at` là ngày kiểm tra tham chiếu trong đợt rà soát này, không chứng minh nguồn truy cập trực tiếp thành công hay pinpoint đã được xác thực. `pinpoint_validation_status` và `review_status` còn chờ chuyên gia. Không bịa trích đoạn nguyên văn từ PDF scan hoặc điền số trang khi chưa đối chiếu được. Các trường `clause`, `point` để trống khi văn bản không có cấp tương ứng.

`source_kind=official_document_record` là trang hồ sơ văn bản chính thức; cần mở bản gốc đính kèm để kiểm tra đoạn. `official_explanation` là bài giải thích trên cổng Chính phủ có dẫn văn bản, không phải chính văn và không được nâng thành văn bản quy phạm. Hai nguồn giải thích hỗ trợ câu giảm trừ gia cảnh và tiền ăn giữa ca cần bổ sung liên kết chính văn trước khi đóng băng benchmark.

## Nguồn đối chiếu

- [Thông tư 219/2013/TT-BTC](https://vanban.chinhphu.vn/?docid=172570&pageid=27160) và [bản gốc PDF](https://datafiles.chinhphu.vn/cpp/files/vbpq/2014/02/tt-219.pdf): VAT lịch sử.
- [Thông tư 26/2015/TT-BTC](https://vanban.chinhphu.vn/?docid=179270&pageid=27160): sửa Điều 15 về thanh toán, đọc cùng bản gốc.
- [Thông tư 96/2015/TT-BTC](https://vanban.chinhphu.vn/?docid=180650&pageid=27160) và [bản gốc PDF](https://datafiles.chinhphu.vn/cpp/files/vbpq/2015/07/96.signed_01.pdf): Điều 4 thay Điều 6 Thông tư 78/2014/TT-BTC.
- [Thông tư 78/2014/TT-BTC](https://vbpl.moj.gov.vn/vinhlong/Pages/vbpq-toanvan.aspx?ItemID=46368&Keyword=): chuyển lỗ, thuế suất và bù trừ phạt hợp đồng. Trang toàn văn có lỗi truy cập trong phiên rà soát; không coi đây là kết quả kiểm tra liên kết thành công.
- [Thông tư 111/2013/TT-BTC](https://vanban.chinhphu.vn/?docid=169566&pageid=27160) và [bản gốc PDF](https://datafiles.chinhphu.vn/cpp/files/vbpq/2013/09/tt-111.pdf): PIT lịch sử; kiểm tra bản sửa đổi cho từng điều.
- [Thông tư 06/2018/TT-BTC](https://vbpl.vn/nganhangnhanuoc/Pages/vbpq-toanvan.aspx?ItemID=128846&Keyword=): sửa danh mục phúc lợi tại khoản 4 Điều 3; trang toàn văn có lỗi truy cập trực tiếp trong phiên rà soát.
- [Nghị định 123/2020/NĐ-CP](https://chinhphu.vn/default.aspx?docid=201365&pageid=27160) và [bản gốc PDF](https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/10/123.signed_01.pdf): dùng phiên bản năm 2024, không mặc định cho hóa đơn sau sửa đổi năm 2025.
- [Giải thích về giảm trừ gia cảnh](https://cms.baochinhphu.vn/cuc-thue-luu-y-khi-quyet-toan-va-hoan-thue-tu-dong-102260305191148461.htm): đối chiếu mức lịch sử Nghị quyết 954/2020/UBTVQH14; không áp dụng mức năm 2024 cho năm 2026.
- [Giải thích về tiền ăn giữa ca](https://cms.baochinhphu.vn/xac-dinh-thu-nhap-chiu-thue-khoan-chi-an-ca-cho-nguoi-lao-dong-102251030101936343.htm): dẫn điểm g.5 khoản 2 Điều 2 Thông tư 111 và khoản 4 Điều 22 Thông tư 26/2016/TT-BLĐTBXH, đồng thời phân biệt thay đổi từ 15/06/2025.

## Thẩm định và mở rộng

RFP trang 23, EVAL 01 yêu cầu 200 câu trả lời được và 50 câu không trả lời được hoặc mơ hồ, ít nhất 60 câu trả lời được cho mỗi VAT/CIT/PIT, 20 câu hỗ trợ, 40 trường hợp lịch sử/sửa đổi và 30 trường hợp xung đột; các tập con có thể giao nhau. Bộ 30 câu hiện tại không thay thế yêu cầu đó.

Theo EVAL 02, cần hai chuyên gia độc lập kiểm tra căn cứ, kết luận, giả định và claim; phân xử bất đồng, gắn passage ID và snapshot nguồn trước khi chấm. Các URL đang trỏ hồ sơ văn bản hoặc bài giải thích chưa đáp ứng đầy đủ CIT 01–03. Việc truy cập nguồn công khai không đồng nghĩa đã được cấp mọi quyền trích xuất, lưu trữ, xuất bản hoặc xử lý mô hình: phải hoàn tất source/rights register theo CIT 05 trước ingestion.
