# SCRUM-32 — Hỏi làm rõ và kiểm soát căn cứ

## Cơ sở đối chiếu

- Backend: `0ae362f390d021a0874f436c9512a032df882656` (nhánh 08).
- Parser/registry: `c492a6ff0b99cd9762b1fce35d3e607017a41534`.
- Nhánh của An: `a1fa228eea1b58a38ba6507340703c4a099ecb38`; giữ bản sửa Khoản 0 -> null.
- Đã đọc luồng API lưu `research_result` và audit log, không thay object sáu phần hoặc review_status.

## Triển khai

1. Hỏi dữ kiện riêng cho thuế suất hàng hóa và cư trú; không gọi assessor/generator khi thiếu trường trọng yếu.
2. `ResearchRequest` có hai trường tùy chọn tương thích ngược: clarification_scenario và case_facts.
3. effective_date/version/status ở passage lấy từ CHUNK, không lấy từ DOCUMENT. Thiếu metadata cấp đoạn giữ null. Metadata cấp văn bản giữ riêng document_effective_date/document_version; expiry_date hiện là ngày hết hiệu lực văn bản vì model đoạn chưa có trường này. Không suy luận null là đang có hiệu lực.
4. ResearchContext thêm scenario/case_facts; dữ liệu cấu trúc được che trước khi gọi AI và lưu vào material_facts đã che để mở lại lịch sử. Không yêu cầu gửi số giấy tờ, địa chỉ hay ảnh giấy tờ trong câu hỏi cư trú.
5. EvidenceAssessment giữ passage_id/sufficient và thêm reason_code (mặc định not_assessed để tương thích callback cũ). Enum: not_assessed/sufficient/irrelevant/temporal_unknown/conflict/missing_facts/unsupported.
6. ResearchResult thêm assessment_records. Mỗi bản ghi chứa ID, sufficient/decision, reason_code, phiên bản/ngày/trạng thái của đoạn và SHA-256 của passage đã chuẩn hóa/che.
7. Backend ghi `research.guardrail` vào bảng audit_logs hiện có, cùng transaction với history. Không cần migration DB. Audit lưu policy_version/status/reason/assessment_records, không lưu prompt, toàn văn hay exception provider. Không thay đổi contract sáu phần để tránh ảnh hưởng exporter/frontend.
8. Các callback do server cung cấp qua dependency research_callbacks. Client không cung cấp assessment/allowed IDs/approval. AI vẫn chỉ tạo draft; chuyên gia mới quyết định review_status.

## Giao diện hỏi bổ sung

```json
{
  "matter_id": "UUID hồ sơ",
  "question": "Thuế suất GTGT của hàng hóa này?",
  "tax_period": "2099",
  "clarification_scenario": "goods_rate",
  "case_facts": {
    "goods_description": "Mô tả hàng giả lập",
    "transaction_type": "Bán nội địa",
    "transaction_date": "2099-02"
  }
}
```

Với residency, case_facts dùng presence_period/accommodation/foreign_residency. Có thể ghi rõ không có chỗ ở/không có giấy xác nhận; không gửi dữ liệu nhận dạng. Giá trị trống, unknown, không rõ, chưa biết, chưa xác định tiếp tục được hỏi lại. Không tự rút trường từ đoạn văn tự do: client/Backend nên chuyển câu trả lời đã xác nhận vào case_facts. Không chọn scenario thì nhận diện bằng từ khóa; đây là heuristic, không phải phân loại pháp lý đầy đủ. Khi không nhận diện, quy tắc hỏi chung trước đây vẫn áp dụng. Trường không rỗng chưa chứng minh đủ ngữ cảnh; assessor vẫn phải kiểm tra.

## Hợp đồng assessor/generator

- Assessor: `(SafeResearchInput) -> Sequence[EvidenceAssessment]`, nhận nguồn đúng quyền, toàn văn đã che, metadata cấp đoạn. Chỉ đánh dấu sufficient=True sau khi kiểm tra nguồn đủ hỗ trợ toàn câu hỏi, kỳ áp dụng, xung đột và chuyển tiếp. Có score hoặc metadata đầy đủ không tự động cho phép sinh.
- Generator: `(SafeResearchInput) -> dict | JSON str | GeneratedResearch`, chỉ nhận nguồn được assessor chấp nhận. JSON phải tuân thủ draft/clarify/abstain và sáu phần.
- Không có assessor -> abstain. Đánh giá unknown/False -> không cho sinh. reason_code dùng mã có kiểm soát, không dùng văn bản lỗi tự do. Callback cũ không có reason_code vẫn chạy nhưng audit hiển thị not_assessed (chưa cung cấp lý do), không giả lập lý do mới.
- SHA-256 dùng nhận biết snapshot đã đánh giá, không thay thế kho snapshot toàn văn hoặc xác nhận nguồn còn truy hồi được. Metadata phiên bản “1.0” vẫn chỉ là giá trị trong registry.

## Kiểm thử

Từ gốc repository, Python 3.10+:

```powershell
python -m pip install -r backend/requirements.txt
python -m unittest discover -s tests/guardrails -v
$env:PYTHONPATH = "$PWD;$PWD\backend"
python -m pytest backend/tests -q
```

Backend test mặc định dùng SQLite `test.db`, tạo/xóa bảng trong từng test. Không đặt TEST_DATABASE_URL tới DB dev/prod. Kết quả máy thực thi: 58 test guardrails; 117 Backend test đạt, 1 test được bộ test gốc đánh dấu skip. Provider giả lập; không gọi AI trả phí, không xác nhận luật thật. Đã kiểm thử API lưu/mở lịch sử, audit, ID ngoài nguồn, thiếu citation, dữ liệu nhạy cảm và provider trả approved.

## Tích hợp/giới hạn

Dựa trên nhánh Backend mới nhất chứ không trên ZIP SCRUM-23 cũ. Bản vá gồm thay đổi nhỏ ở source schema, research endpoint, matter_service và adapter; cần Luân review các file này. Không chép đè toàn bộ thư mục Backend.

Frontend chưa có form case_facts: có thể gọi API/Swagger để kiểm thử trước. LLM provider/assessor thật chưa được cấu hình; mặc định vẫn từ chối. Kiểm tra ID/cấu trúc không chứng minh quan hệ ngữ nghĩa claim-nguồn. Metadata không tự giải quyết tính áp dụng. Regex redaction còn giới hạn với tên, địa chỉ và số bị viết cách nhóm. Câu hỏi cư trú chỉ thu thập thông tin, không mã hóa điều kiện pháp luật hoặc kết luận cư trú.
