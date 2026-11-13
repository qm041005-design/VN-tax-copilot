# Gói phối hợp tuần 3 — phần trưởng nhóm

Trạng thái: sẵn sàng gửi nhóm góp ý; chưa có xác nhận của các thành viên. Phạm vi hiện tại chỉ là chuẩn bị quy ước, JSON mẫu và tình huống kiểm thử. Không merge hoặc thay code của thành viên trong bước này.

## 1. Mọi người đọc gì?

1. [DATA_CONTRACT.md](DATA_CONTRACT.md): API đang có, bảng ánh xạ và các đề xuất.
2. [JSON mẫu](examples/week3_data_contract.json): minh họa kiểu dữ liệu. Toàn bộ nguồn trong mẫu là giả lập.
3. [10 tình huống kiểm thử](../../evaluation/WEEK_3_INTEGRATION.md): cách chuẩn bị, chạy và ghi kết quả.

Tiếp tục dùng API hiện tại của Luân để nối hồ sơ, tìm kiếm và xem nguồn. Không chờ tính năng sinh câu trả lời mới làm các phần này. Các mở rộng chưa có như history.research_result cần xác nhận trước khi triển khai.

## 2. Mỗi bạn cần phản hồi ngay

| Người | Nội dung cần xác nhận | Trạng thái |
|---|---|---|
| Duyên | article_number dạng chuỗi; Khoản 0/Điểm rỗng chuyển null; nguồn/trang/phiên bản có thể cung cấp đến đâu; phối hợp Luân về model và migration | Chờ phản hồi |
| Thanh | Nhận passage_id/text cùng metadata; không làm rơi ID; trả top 10 cho QA; thống nhất với Luân cách thay tìm kiếm SQL hiện có | Chờ phản hồi |
| Luân | source_id là mã đoạn; ánh xạ sang passage_id; cách lấy SourceDetail toàn văn; đề xuất lưu research_result và phiên bản nguồn | Chờ phản hồi |
| Phước | Dùng đúng SourceHit/SourceDetail; phân biệt nguồn tìm được với nguồn hỗ trợ câu trả lời; không trộn trạng thái hồ sơ, tổng hợp và thẩm định | Chờ phản hồi |
| An | Cách truyền kết quả kiểm tra đủ căn cứ; xử lý thiếu dữ kiện, thiếu nguồn và dữ liệu nhạy cảm | Chờ phản hồi |
| Đan | Rà 10 ca phát triển, ánh xạ ID với benchmark; giữ riêng bộ benchmark 250 ca; thống nhất cách lưu kết quả chạy | Chờ phản hồi |

Mẫu phản hồi: “Module …; đồng ý các mục …; cần đổi mục … vì …; trường chưa có …; dự kiến cung cấp đầu ra mẫu vào …”. Quân tổng hợp quyết định thực tế, không đánh dấu đã đồng ý thay người khác.

## 3. Làm song song thế nào?

- Quân: hoàn thiện quy ước theo phản hồi, chuẩn bị adapter prompt/Word sau khi chốt.
- Duyên: sửa parser/registry theo dữ liệu đã thống nhất.
- Thanh: làm tìm kiếm bằng passage mẫu, sau đó thay bằng dữ liệu Duyên.
- Luân và Phước: nối API hồ sơ/tìm kiếm/xem nguồn/lịch sử hiện có; phối hợp về phần API mở rộng.
- An và Đan: chuẩn bị kiểm tra hành vi và căn cứ. Không tạo đánh giá đủ căn cứ giả cho dữ liệu luật thật.
- Phúc: dùng quy ước cấu hình mà backend/frontend thống nhất; phần Docker/CI được xử lý ở task riêng.

Mỗi bạn mở PR khi có phần chạy được, kèm commit, hướng dẫn chạy, kết quả test và giới hạn. Chỉ khi có dữ liệu thật mới kết luận luồng tích hợp đã chạy; fixture không thay thế bằng chứng đó.

## 4. Tin nhắn Quân có thể gửi nhóm

> Mọi người ơi, mình đã chuẩn bị bản quy ước dữ liệu tuần 3 dựa trên API của Luân, kèm JSON mẫu và 10 tình huống kiểm thử. Duyên, Thanh, Luân, Phước xem giúp bảng ánh xạ; An và Đan xem phần kiểm tra căn cứ/trạng thái và bộ tình huống nhé. Mỗi bạn phản hồi trường nào đồng ý, trường nào chưa có hoặc cần đổi trước khi triển khai phần phụ thuộc. Những phần API hiện có vẫn tiếp tục làm song song. Khi có phần chạy được, mọi người mở PR và gửi hướng dẫn cùng kết quả test để mình kiểm tra dần. Tài liệu hiện là đề xuất chờ xác nhận, chưa phải toàn bộ chức năng đã được triển khai.

## 5. Việc để sau khi nhóm có đầu ra

Quân sẽ cập nhật prompt/xuất Word, chạy bộ tình huống với kết quả thật và kiểm tra tích hợp. Bước chuẩn bị này không bao gồm triển khai các adapter, thay đổi API, gọi AI trả phí hoặc tổng hợp báo cáo tuần.
