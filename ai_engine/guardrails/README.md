# SCRUM-11 — Lọc thông tin cá nhân và bộ từ chối

Python 3.10+, chỉ dùng thư viện chuẩn. Chạy từ thư mục gốc repository:

```bash
python -m unittest discover -s tests/guardrails -v
```

## Luồng tích hợp Backend/RAG

1. Không ghi log request hoặc nguồn thô. Dùng `prepare_research` trước khi gửi dữ liệu ra ngoài.
2. Truy xuất nội bộ có thể dùng câu hỏi thô nếu hệ thống tìm kiếm được phép xử lý dữ liệu đó. Nếu search dùng dịch vụ bên ngoài, che câu hỏi bằng `redact_text` trước cả bước search.
3. Component đánh giá nhận câu hỏi và nguồn đã che, kiểm tra nguồn có đủ căn cứ cho câu hỏi, kỳ thuế, hiệu lực và mâu thuẫn. Component này chưa có trong SCRUM-11. Khi chưa được tích hợp, hệ thống mặc định từ chối.
4. Gọi `decide_abstention`. Nếu từ chối, trả thông báo và KHÔNG gọi LLM sinh câu trả lời.
5. Nếu được phép, chỉ chuyển các nguồn có ID nằm trong `evidence_ids` sang bước sinh. Sau sinh vẫn cần Citation Validator riêng và chuyên gia duyệt.

```python
from ai_engine.guardrails import prepare_research, decide_abstention

# hits là list dict BM25: passage_id, legal_identifier, text, score.
safe = prepare_research(question, hits)
# assess_evidence do nhóm tích hợp; phải nhận safe.query và safe.passages.
assessments = assess_evidence(safe.query, safe.passages)
decision = decide_abstention(safe.query, safe.passages, assessments)
if decision.should_abstain:
    response = {"status": "abstained", "reason": decision.reason,
                "message": decision.message}
else:
    selected = [p for p in safe.passages if p["passage_id"] in decision.evidence_ids]
    response = generate_answer(safe.query, selected)
```

`assess_evidence` và `generate_answer` là các điểm tích hợp, không phải hàm được cung cấp trong module này. Component đánh giá trả `EvidenceAssessment(passage_id, sufficient=True/False/None)` từ kết quả kiểm tra đáng tin cậy, không lấy cờ `sufficient` từ HTTP request hoặc mặc định True cho mọi hit. Không dùng điểm BM25 làm xác suất; chưa đặt ngưỡng tùy ý.

## Chính sách che dữ liệu phiên bản đầu

| Dữ liệu | Phạm vi nhận diện |
| --- | --- |
| CCCD | Chuỗi liền 12 chữ số |
| CMND | 9 chữ số sau nhãn CMND |
| MST | 10 chữ số, hoặc 10 + 3 chữ số chi nhánh; ưu tiên nhãn MST/mã số thuế |
| Điện thoại | Di động dạng 0, +84, 0084; cho phép dấu cách, chấm, gạch nối |
| Email | Dạng email thông dụng |

Dùng dữ liệu giả trong test. Kết quả chỉ giữ text đã che và số lượng theo loại; không lưu bảng ánh xạ về dữ liệu gốc. `prepare_research` chỉ cho qua passage_id, text và legal_identifier; metadata khác bị loại. passage_id phải là ID nội bộ không chứa dữ liệu cá nhân. Backend giữ nguồn gốc/URL ở phía server để dựng citation.

## Giới hạn cần biết

Đây là baseline kỹ thuật, chưa phải chứng nhận đáp ứng đầy đủ yêu cầu bảo vệ dữ liệu. Regex có thể bỏ sót tên, địa chỉ, bảng lương, số được viết bằng chữ hoặc chia nhóm; chuỗi 10 chữ số có thể bị che dù là số liệu khác. MST doanh nghiệp cũng bị che theo chính sách thận trọng, cần BA xác nhận. Số điện thoại và MST trùng hình thức có thể nhận nhãn khác nhau nhưng vẫn được che.

Chưa gắn vào endpoint: nhánh develop hiện chỉ có khung Backend. Chưa có mô hình đánh giá mức đủ căn cứ, Citation Validator, kiểm tra hiệu lực văn bản hay xử lý prompt injection. `evidence_available` chỉ cho phép bước sinh có điều kiện, không xác nhận tính đúng của câu trả lời cuối. Cần áp dụng lại redaction ở biên xuất/log nếu câu trả lời hoặc metadata khác có thể chứa dữ liệu cá nhân.


## SCRUM-23

Xem `docs/integration/SCRUM-23.md` cho pipeline mới, adapter sáu phần và bản vá endpoint. Hàm hiện tại sử dụng status draft/clarify/abstain.
