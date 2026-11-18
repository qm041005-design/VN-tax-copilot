# Gói phối hợp tuần 3 — phần trưởng nhóm

Ngày cập nhật: 14/11/2026. Đã có adapter prompt/Word SCRUM-17 và lần chạy 10 ca kỹ thuật; chưa có xác nhận quy ước của các thành viên. PR #11 vẫn chờ review, chưa merge. Không thay code nhánh cá nhân của thành viên.

## 1. Mọi người đọc gì?

1. [DATA_CONTRACT.md](DATA_CONTRACT.md): API đang có, bảng ánh xạ và các đề xuất.
2. [JSON mẫu](examples/week3_data_contract.json): minh họa kiểu dữ liệu. Toàn bộ nguồn trong mẫu là giả lập.
3. [10 tình huống kiểm thử](../../evaluation/WEEK_3_INTEGRATION.md): cách chuẩn bị, chạy và ghi kết quả.

PR #11 tại `028f4bf` trả research_result ở cấp gốc của POST /research; chưa lưu nguyên object này vào lịch sử. Nhánh Luân mới `9b5a1d2` có schema bổ sung cần ghép có chọn lọc. Dùng đúng commit khi đối chiếu API, không coi hai bản tương đương.

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

- Quân: đã thêm adapter prompt/Word và runner 10 ca; tiếp tục xử lý lỗi/phụ thuộc được ghi trong kết quả, chưa Done.
- Duyên: sửa parser/registry theo dữ liệu đã thống nhất.
- Thanh: làm tìm kiếm bằng passage mẫu, sau đó thay bằng dữ liệu Duyên.
- Luân và Phước: nối API hồ sơ/tìm kiếm/xem nguồn/lịch sử hiện có; phối hợp về phần API mở rộng.
- An và Đan: chuẩn bị kiểm tra hành vi và căn cứ. Không tạo đánh giá đủ căn cứ giả cho dữ liệu luật thật.
- Phúc: dùng quy ước cấu hình mà backend/frontend thống nhất; phần Docker/CI được xử lý ở task riêng.

Mỗi bạn mở PR khi có phần chạy được, kèm commit, hướng dẫn chạy, kết quả test và giới hạn. Chỉ khi có dữ liệu thật mới kết luận luồng tích hợp đã chạy; fixture không thay thế bằng chứng đó.

## 4. Tin nhắn Quân có thể gửi nhóm

> Mọi người ơi, mình đã cập nhật quy ước theo PR #11 và nhánh Luân mới, thêm adapter prompt/Word. Chạy 10 ca kỹ thuật được 6 blocked do thiếu nguồn đã duyệt/assessor, 2 fail vì câu hỏi làm rõ còn chung và 2 pass cho abstain bằng fixture. Luân/Duyên xem phần schema và migration; An xem câu hỏi làm rõ; Phước xem research_result và hướng nối tải Word. Các bạn phản hồi điểm đồng ý hoặc cần đổi giúp mình; chưa có xác nhận thì mình vẫn giữ trạng thái chờ. PR #11 chưa merge và SCRUM-17 chưa Done.

## 5. Việc để sau khi nhóm có đầu ra

Đã chạy 10 ca qua TestClient trên SQLite tạm với backend PR #11: **6 blocked, 2 fail, 2 pass kỹ thuật**. W3-001..006 thiếu nguồn đã duyệt/ID/trang và assessor/generator. W3-007..008 trả clarify nhưng chỉ hỏi chung, chưa hỏi đúng dữ kiện hàng hóa/phương pháp thuế hoặc cư trú. W3-009..010 kiểm tra abstain bằng test double/fixture biệt lập, không phải đánh giá pháp lý.

Lệnh chạy, artifact và cách dùng adapter: [WEEK_3_INTEGRATION.md](../../evaluation/WEEK_3_INTEGRATION.md). Kết quả gồm response thật, lịch sử mở lại, các check và hash DOCX tạo trong bộ nhớ. Không có LLM trả phí hoặc báo cáo tuần được tạo.

Phần tiếp theo cần phối hợp: đồng bộ schema/migration backend; câu hỏi làm rõ cụ thể; lưu research_result vào history; endpoint xuất Word và frontend gọi endpoint sau kiểm tra quyền. Chưa coi thư viện xuất bytes là tính năng tải Word end-to-end.
