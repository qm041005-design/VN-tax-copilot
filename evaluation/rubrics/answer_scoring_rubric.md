# VN-TAX-COPILOT — AI Answer Scoring Rubric

**Requirement IDs:** EVAL 01, EVAL 02, EVAL 03, EVAL 04, EVAL 05, EVAL 06, AT 01, AT 02, AT 03, AT 04  
**Version:** 1.0 — Draft  
**Source:** THTax Vietnam Tax Research Copilot RFP, Section 8 and Annex E  
**Status:** Proposed implementation; pending reviewer and project approval

## 1. Mục đích

Tài liệu này quy định cách đánh giá chất lượng câu trả lời của hệ thống VN-TAX-COPILOT trong nghiên cứu pháp luật thuế Việt Nam.

Các nội dung đánh giá gồm:

- Tính chính xác của câu trả lời.
- Tính phù hợp với phạm vi và thời kỳ pháp luật.
- Chất lượng nguồn dẫn chứng.
- Khả năng tìm kiếm chứng cứ.
- Khả năng từ chối trả lời hoặc yêu cầu làm rõ khi thiếu thông tin.

## 2. Cấu trúc bộ Benchmark — EVAL 01

Bộ benchmark gồm 250 câu hỏi tiếng Việt.

| Nhóm | Số lượng |
|---|---:|
| VAT — Thuế giá trị gia tăng | Ít nhất 60 |
| CIT — Thuế thu nhập doanh nghiệp | Ít nhất 60 |
| PIT — Thuế thu nhập cá nhân | Ít nhất 60 |
| Quản lý thuế và hóa đơn điện tử | 20 |
| Không thể trả lời hoặc mơ hồ nghiêm trọng | 50 |
| **Tổng cộng** | **250** |

Trong 200 câu có thể trả lời, phải có ít nhất:

- 40 trường hợp liên quan đến lịch sử pháp luật hoặc sửa đổi văn bản.
- 30 trường hợp liên quan đến các nguồn pháp lý mâu thuẫn.

Các nhóm trường hợp này được phép trùng nhau.

Bộ benchmark phải được chốt tại G1, sau khi có phê duyệt theo quy trình dự án.

## 3. Quy trình đánh giá độc lập — EVAL 02

Mỗi trường hợp kiểm thử phải được hai người đánh giá độc lập có chuyên môn hiện hành về thuế Việt Nam gắn nhãn.

Các nội dung gắn nhãn bằng tiếng Việt:

1. Chứng cứ pháp lý bắt buộc.
2. Kết luận có thể chấp nhận.
3. Các giả định cần thiết.
4. Các nhận định pháp lý quan trọng.

Nếu hai người đánh giá bất đồng, phải thực hiện đối soát và thống nhất trước khi chấm điểm.

Các trường hợp dùng để nghiệm thu không được sử dụng để tinh chỉnh hệ thống. Cần dự phòng các trường hợp thay thế và công bố rủi ro nhiễm dữ liệu đánh giá.

## 4. Tiêu chí chấm câu trả lời — EVAL 03 / AT 01

Mỗi câu hỏi có thể trả lời được đánh giá theo hai trạng thái:

- **PASS:** Đáp ứng đầy đủ các điều kiện.
- **FAIL:** Không đáp ứng ít nhất một điều kiện.

Một câu trả lời chỉ PASS khi:

| Tiêu chí | Điều kiện |
|---|---|
| Chính xác nội dung | Kết luận đúng về bản chất pháp lý |
| Đúng phạm vi | Phù hợp phạm vi câu hỏi và pháp luật áp dụng |
| Đáp ứng yêu cầu | Trả lời đúng vấn đề được hỏi |
| Có điều kiện phù hợp | Nêu giả định, giới hạn hoặc sự không chắc chắn khi cần |
| Có chứng cứ hỗ trợ | Các nhận định quan trọng được hỗ trợ bằng chứng cứ |
| Đúng thời kỳ | Áp dụng đúng thời kỳ pháp luật |
| Đúng thẩm quyền tài phán | Áp dụng đúng pháp luật Việt Nam và phạm vi liên quan |

Áp dụng sai thời kỳ hoặc sai thẩm quyền tài phán là FAIL.

Việc từ chối trả lời một câu hỏi vốn có thể trả lời cũng là FAIL và được tính vào tỷ lệ từ chối không cần thiết.

**Ngưỡng AT 01:** Ít nhất 90% trong 200 câu hỏi có thể trả lời phải đạt PASS.

## 5. Đánh giá chất lượng dẫn chứng — EVAL 04 / AT 02

### 5.1. Citation Existence and Pinpoint Validity

Công thức:

Citation Validity = Số lượt trích dẫn hợp lệ / Tổng số lượt trích dẫn

Một trích dẫn hợp lệ phải tồn tại và dẫn đến đúng vị trí chứng cứ.

**Ngưỡng:** Ít nhất 98%.

### 5.2. Claim Support Precision

Công thức:

Support Precision = Số cặp nhận định–trích dẫn thực sự hỗ trợ nhau / Tổng số cặp nhận định–trích dẫn

**Ngưỡng:** Ít nhất 95%.

### 5.3. Material Claim Coverage

Công thức:

Claim Coverage = Số nhận định quan trọng có chứng cứ hỗ trợ / Tổng số nhận định quan trọng

**Ngưỡng:** Ít nhất 95%.

Người đánh giá phải liệt kê cả những nhận định quan trọng bị bỏ sót để tránh việc hệ thống đạt điểm cao bằng cách lược bỏ nội dung khó.

**Điều kiện bắt buộc:** Không có văn bản pháp luật hoặc đoạn trích dẫn được bịa đặt trong bộ nghiệm thu.

## 6. Đánh giá Recall@10 — EVAL 05 / AT 03

Recall@10 đo khả năng hệ thống tìm được các chứng cứ cần thiết trong 10 đoạn văn bản được truy xuất đầu tiên.

Công thức cho từng câu hỏi:

Recall@10 = Số chứng cứ bắt buộc được tìm thấy trong Top 10 / Tổng số chứng cứ bắt buộc do chuyên gia gắn nhãn

Kết quả chung là trung bình cộng Recall@10 của 200 câu hỏi có thể trả lời.

**Ngưỡng AT 03:** Recall@10 ≥ 90%.

Yêu cầu:

- Chỉ đánh giá trên 200 câu hỏi có thể trả lời.
- Chứng cứ bắt buộc phải được chuyên gia gắn nhãn.
- Thống nhất đơn vị chứng cứ và các nguồn tương đương được chấp nhận trước khi đánh giá.
- Báo cáo kết quả theo nguồn và nhóm thuế.

## 7. Đánh giá từ chối và làm rõ — AT 04

Với 50 câu hỏi không thể trả lời hoặc mơ hồ nghiêm trọng:

- Ít nhất 90% phải được từ chối hoặc yêu cầu làm rõ một cách chính xác.

Với 200 câu hỏi có thể trả lời:

- Tỷ lệ từ chối không cần thiết không được vượt quá 10%.

## 8. Báo cáo kết quả — EVAL 06

Báo cáo đánh giá phải ghi nhận:

- Tử số và mẫu số của từng chỉ số.
- Các trường hợp thất bại.
- Khoảng tin cậy 95% cho các tỷ lệ.
- Kết quả so sánh tìm kiếm chỉ bằng từ khóa với hệ thống Copilot.
- Thời gian nghiên cứu và chi phí.

Các ngưỡng số học áp dụng cho giá trị ước lượng điểm.

Không tự khẳng định mức tiết kiệm năng suất tối thiểu khi chưa có nghiên cứu được xác định rõ.

## 9. Quy tắc nghiệm thu

Kết quả đánh giá phải sử dụng bộ dữ liệu và phiên bản hệ thống được đóng băng theo quy trình nghiệm thu.

Việc đạt tỷ lệ trung bình không được dùng để bỏ qua các lỗi bắt buộc về an toàn, bảo mật hoặc nguồn pháp lý giả mạo.

Mọi bất đồng chuyên môn phải được ghi nhận và giải quyết theo quy trình đánh giá độc lập.

## 10. Trạng thái tài liệu

Tài liệu này là bản dự thảo triển khai dựa trên THTax RFP.

Chỉ được coi là rubric nghiệm thu chính thức sau khi được nhóm dự án và các bên đánh giá có thẩm quyền phê duyệt.