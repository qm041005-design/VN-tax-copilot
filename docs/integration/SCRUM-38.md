# SCRUM-38 — Nối provider với đánh giá căn cứ

## Phạm vi và nền code

Bản vá dựa trên Backend SCRUM-36 commit `ca4c32fd27a0f612f1c439f905fbb5fc6c9c6669` ngày 27/11/2026, gồm SCRUM-32 của An và prompt/adapter tuần 4 của Quân. Không viết lại `research_callbacks` hay `make_guarded_generator`.

- `ai_engine.guardrails.llm_assessor:assess` khớp `assess(SafeResearchInput) -> list[EvidenceAssessment]`.
- `ai_engine.providers.chat_json:complete` khớp `complete(messages) -> dict`.
- Callback do server nạp; không có API nhận key, URL, callback hoặc cờ sufficient từ client.
- Transport chỉ là giao thức HTTPS Chat Completions JSON. Chưa chọn nhà cung cấp hoặc model thay nhóm. Không tự gọi endpoint, không mặc định key/model, không SDK riêng. Hỗ trợ thực tế của dịch vụ/model phải được xác nhận trước khi dùng.

## Luồng

Quyền hồ sơ -> tìm nguồn -> hỏi bổ sung -> che dữ liệu -> kiểm tra metadata -> assessor -> chỉ nguồn được chấp nhận -> generator qua prompt Quân -> validate JSON/citations -> redaction đầu ra -> lưu history và audit.

- Thiếu dữ kiện thông thường/hàng hóa/cư trú: clarify trước lời gọi AI.
- Nguồn thiếu ngày hiệu lực cấp đoạn/phiên bản hoặc status khác CON_HIEU_LUC: trả đánh giá unknown/temporal_unknown, không gọi model, không tự bỏ nguồn chưa rõ để duyệt phần còn lại. Đây là policy bảo thủ của bản đầu, cần Quân/nhóm dữ liệu review. Không thay null bằng metadata văn bản. Dữ liệu pilot hiện có CHUA_XAC_DINH sẽ bị chặn đúng policy này.
- Đủ metadata chỉ cho phép gọi assessor, không tự chứng minh đủ căn cứ. Assessor dùng prompt yêu cầu xem ngữ cảnh, kỳ áp dụng, chuyển tiếp, xung đột và mức hỗ trợ toàn câu hỏi. Kết quả phải đủ ID, duy nhất, đúng kiểu boolean/null, đúng mã lý do. Các cờ tổng context_complete/query_supported/conflicts_resolved phải là bool.
- context_complete=false -> ghi reason missing_facts và clarify; query_supported=false/conflicts_resolved=false -> không cho generator chạy. Khẳng định sufficient true đòi reason_code sufficient.
- Không có đánh giá đủ căn cứ -> abstain; JSON lỗi/ID lạ/approved -> chặn. Không có cơ chế tự phê duyệt.

## Cấu hình opt-in

Đặt trong `.env` tại working directory chạy Backend (quy ước hiện có của settings) hoặc biến môi trường. Không commit file `.env`. Thêm các biến mẫu vào backend/.env.example nhưng mặc định AI vẫn tắt.

```dotenv
RESEARCH_ASSESSOR=ai_engine.guardrails.llm_assessor:assess
RESEARCH_COMPLETION=ai_engine.providers.chat_json:complete
RESEARCH_AI_ENABLED=false
RESEARCH_AI_URL=
RESEARCH_AI_MODEL=
RESEARCH_AI_API_KEY=
RESEARCH_AI_TIMEOUT=30
RESEARCH_AI_MAX_TOKENS=4096
```

Chỉ sau khi nhóm chốt endpoint/model hỗ trợ giao thức và có key riêng: điền URL HTTPS đầy đủ của endpoint chat completions, model và key; đổi ENABLED=true rồi restart server. Không chụp/log file env hoặc request headers. Hai bước assessor/generator có thể tốn hai lời gọi AI cho một câu hỏi. Không có retry tự động.

Transport gửi model/messages/response_format=json_object/max_completion_tokens; nhận choices[0].message.content dạng JSON object, finish_reason=stop. Nếu nhà cung cấp không hỗ trợ tham số này cần adapter khác hoặc sửa có test; đây không phải adapter Gemini native/Responses API. Không đổi tên endpoint rồi giả định mọi dịch vụ tương thích.

Tham chiếu giao thức: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create . JSON mode không bảo đảm schema/ngữ nghĩa, vì vậy luôn validate ở assessor và guardrails.

## Lỗi và audit

Các mã an toàn: provider_disabled/configuration/timeout/auth/rate_limit/http/network/invalid_output/limit (đều có tiền tố provider_). Public message cố định, không mang upstream error body, exception text, key, URL hoặc prompt. Pipeline ghi status/reason vào audit research.guardrail hiện có cùng transaction với history; giữ assessment_records nếu generator lỗi sau khi đã đánh giá.

HTTPS bắt buộc; key chỉ trong Authorization header. Không chuyển hướng, không dùng proxy môi trường hoặc retry ngầm. Timeout 1–120 giây cho từng thao tác HTTP; đây không phải deadline toàn bộ HTTP request hoặc toàn pipeline. Giới hạn request 256 KB và decoded response 1 MB. Không cắt nguồn âm thầm khi quá giới hạn. Không log payload. Cấu hình sai không hiển thị giá trị bí mật.

## Chạy test trên Windows

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m pip install -r backend/requirements.txt
.\.venv312\Scripts\python.exe -m unittest discover -s tests/guardrails -v
$env:PYTHONPATH = "$PWD;$PWD\backend"
.\.venv312\Scripts\python.exe -m pytest backend/tests -q
.\.venv312\Scripts\python.exe -m ai_engine.providers.demo_scrum38
```

Kết quả kiểm tra bản vá: 78 unit test guardrails đạt; 137 Backend test đạt, 1 skipped trên SQLite. Chạy thêm toàn bộ bộ test được pytest.ini thu thập: 264 passed, 1 skipped. Demo chạy sáu ca clarify/insufficient/draft/unknown_id/timeout/auth bằng httpx.MockTransport, không có network thật. Backend test dùng chính callback path cấu hình + adapter thật của Quân + HTTP giả lập; kiểm tra lưu/mở lại history, audit, các lỗi và redaction. Không cấu hình TEST_DATABASE_URL tới DB dev/prod vì bộ Backend test tạo/xóa bảng.

## Minh chứng và nghiệm thu

Đính kèm ảnh test + demo giả lập, commit và PR. Chưa được ghi “đã kết nối model thật” hoặc “đã nghiệm thu pháp lý”. Khi nhóm có provider, bổ sung smoke test opt-in với dữ liệu công khai/giả lập và ghi endpoint loại giao thức, model, thời điểm, status/call count; không lưu key/request headers/raw lỗi. Một smoke thành công không chứng minh chất lượng câu trả lời hay chống prompt injection đầy đủ.

## Giới hạn

Đánh giá bằng LLM không phải xác minh pháp lý độc lập: cùng model có thể đánh giá sai, bị prompt injection hoặc tự xác nhận nguồn không đủ. Không có verdict chuyên gia, kiểm tra claim-nguồn sau sinh hoặc kiểm chứng chuyển tiếp bằng registry độc lập trong task này. ID hợp lệ không chứng minh nội dung đúng. Câu hỏi bổ sung do assessor phát hiện thêm dùng thông báo an toàn chung; các câu hỏi hai tình huống cụ thể vẫn do SCRUM-32 thu thập.

Redaction regex hiện có vẫn có thể bỏ sót tên/địa chỉ/bảng lương/số chia nhóm; cần dữ liệu giả lập cho thử nghiệm. Giới hạn kích thước không thay thế ngân sách token, rate limit ứng dụng hoặc kiểm thử tải. Audit snapshot hash không thay kho nguồn phiên bản. Chưa chạy live provider, PostgreSQL, Docker hoặc toàn bộ UI trong lượt này.
