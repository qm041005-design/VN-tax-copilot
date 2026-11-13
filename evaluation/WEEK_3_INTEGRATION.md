# Hướng dẫn 10 tình huống kiểm thử tích hợp tuần 3

Dữ liệu: [week3_integration_cases.json](datasets/week3_integration_cases.json).

Đây là bộ tình huống phát triển, không phải benchmark nghiệm thu 250 câu. Kế thừa câu hỏi và nguồn ứng viên từ seed hiện có; không xác nhận lại kết luận pháp lý. Mọi ca đều đang `not_run`, chưa có đánh giá chuyên gia. Không dùng bộ này để công bố đạt chỉ tiêu RFP.

## 1. Danh sách ca

| Mã | Câu seed | Tình huống | Hành vi mong đợi sau khi tích hợp |
|---|---|---|---|
| W3-001 | SEED-VAT-01 | Khấu trừ GTGT, thanh toán tiền mặt, kỳ 2024 | draft nếu đã xác minh đủ nguồn và dữ kiện |
| W3-002 | SEED-VAT-02 | Điều kiện áp dụng với xuất khẩu, kỳ 2024 | draft có nguồn cho các điều kiện liên quan |
| W3-003 | SEED-CIT-01 | Chi trang phục bằng tiền, kỳ trong seed | draft, kiểm tra nguồn và phiên bản áp dụng |
| W3-004 | SEED-CIT-03 | Chuyển lỗ TNDN | draft có căn cứ, không áp luật mới mặc định |
| W3-005 | SEED-PIT-03 | Chuyển nhượng bất động sản cha–con | draft dựa trên tình tiết và nguồn đã duyệt |
| W3-006 | SEED-PIT-05 | Tiêu chí số ngày cư trú | draft giới hạn kết luận đúng nội dung câu hỏi |
| W3-007 | SEED-AMBIGUOUS-02 | Thiếu thông tin phân loại hàng và kỳ áp dụng | clarify, hỏi lại dữ kiện cụ thể |
| W3-008 | SEED-AMBIGUOUS-05 | Thiếu dữ kiện xác định cư trú | clarify, không tự suy ra từ nơi làm việc |
| W3-009 | SEED-VAT-01 | Cố ý cho kết quả truy xuất rỗng | abstain, không bịa nguồn hoặc kết luận |
| W3-010 | SEED-CIT-03 | Có nguồn nhưng chưa xác minh khả năng áp dụng | abstain nếu sau đánh giá vẫn chưa đủ căn cứ |

6 ca draft là mục tiêu có điều kiện. Chưa xác minh được nguồn thì ca đó bị chặn do thiếu tiền đề; không ép hệ thống trả draft để vượt test. Điểm top 10 cao hoặc URL mở được không phải chứng nhận đủ căn cứ.

## 2. Cách chuẩn bị và chạy

1. Tạo hồ sơ thử nghiệm biệt lập bằng tài khoản được phép. Lấy UUID thực thay `request_template.matter_id=null`; không gửi template nguyên trạng đến API.
2. Với W3-001 đến W3-006, đối chiếu candidate_evidence với văn bản gốc và các sửa đổi áp dụng cho kỳ thuế. Điền source_id, acceptable_passage_ids và trang PDF từ registry thật. Không tạo mã nguồn tùy ý. Nguồn chưa có trong kho thì ghi blocker, không coi là lỗi trả lời hoặc PASS.
3. Các `source_pages=[]` và ID null trong JSON có nghĩa chưa ánh xạ, không có nghĩa nguồn đã sẵn sàng. Chưa thu thập đủ trang luật thì cần OCR/parser bổ sung trước khi chạy phần tích hợp này.
4. W3-007 và W3-008 phải dùng hồ sơ không tự bổ sung dữ kiện đang thiếu. Nếu hồ sơ đã có thông tin đó thì đây là tình huống khác; không bắt hệ thống hỏi lại vô ích.
5. W3-009 dùng test double trả danh sách nguồn rỗng. W3-010 dùng nguồn thử nghiệm biệt lập với trạng thái áp dụng chưa xác minh và đánh giá không đủ căn cứ; không sửa kho dữ liệu dùng chung.
6. Gọi API tra cứu hiện có để kiểm tra hồ sơ/nguồn/lịch sử. Hiện backend chưa tổng hợp bằng AI: answer=null không phải PASS cho draft/clarify/abstain. Phần kiểm tra trạng thái tổng hợp đánh dấu blocked đến khi pipeline tương ứng được nối.
7. Khi pipeline sẵn sàng, kiểm tra các assertions, ID trích dẫn, nội dung nguồn hỗ trợ, và kết quả xuất Word. Người có chuyên môn phải kiểm tra kết luận pháp lý riêng.
8. Ghi kết quả theo commit đang chạy, người thực hiện và artifact bằng chứng. Không chép giá trị expected sang actual_result.

## 3. Quy ước ghi kết quả

Trong bản kết quả chạy riêng, dùng execution.status là `not_run`, `blocked`, `pass` hoặc `fail`; điền actual_result, blockers và evidence_artifact. Giữ dataset đầu vào làm mốc, lưu kết quả từng lần tại `evaluation/results/` khi thực sự chạy.

Ghi tối thiểu: mã ca, SHA backend/search/AI, ngày chạy, người chạy, ID nguồn/phiên bản, trạng thái thực tế, lỗi và đường dẫn bằng chứng. Không đưa token hoặc thông tin khách hàng vào artifact.

## 4. Phối hợp với benchmark của Đan

Schema benchmark ở nhánh Đan hiện yêu cầu đúng 250 ca, ID VN-TAX-xxx, hai reviewer và các trường nhãn chuyên môn. Bộ tuần 3 dùng ID W3-xxx và tiền đề kiểm thử kỹ thuật riêng, vì vậy không đưa trực tiếp vào script Recall@10 nghiệm thu và không nới schema 250 để nó chạy.

Khi có nguồn đã duyệt, Đan có thể chuyển các câu phù hợp thành ca phát triển theo schema chung, giữ liên kết seed_case_id, bổ sung nhãn và reviewer thật. Không đưa câu đã dùng để phát triển vào holdout bí mật rồi công bố kết quả không thiên lệch. Điểm Recall@10 của tập nhỏ, nếu đo riêng, phải ghi rõ số ca và chỉ là kết quả phát triển.

Các văn bản tham chiếu được kế thừa từ seed, không phải lời tư vấn thuế mới hoặc kết luận đã được thẩm định.
