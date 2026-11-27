# Prompt tuần 4 — bàn giao cho backend và guardrails

Ngày: 20/11/2026. Nền tích hợp: SCRUM-32 `8eadcd2` (bao gồm backend
lưu lịch sử và xuất Word của Luân). Chưa bao gồm toàn bộ SCRUM-30/31/28 mới.

## Phần đã triển khai

- Prompt có phiên bản `week4-2026-11-20`, giữ đúng bốn khóa đầu ra và sáu phần
  `issue`, `facts`, `authority`, `analysis`, `limitations`, `next_steps`.
- Phân biệt metadata đoạn/văn bản và giá trị chưa biết; hướng dẫn hỏi làm rõ
  theo dữ kiện còn thiếu, không tự bổ sung quy định từ trí nhớ.
- `build_backend_messages` giữ các trường ngữ cảnh bổ sung. Đây là hàm cấp thấp:
  caller phải kiểm tra quyền và che dữ liệu trước khi dùng với provider.
- `make_guarded_generator(complete)` nối hàm gọi model do server cấu hình với
  `run_guarded_research`; dùng lại validator của An để kiểm tra JSON/trích dẫn.
- Với SCRUM-32, dữ kiện `case_facts` đã được guardrails che và ghép vào
  `SafeResearchInput.material_facts`. Adapter không đọc lại request thô.

## Cách Luân/An nối provider

```python
from ai_engine.synthesis.backend_adapter import make_guarded_generator

# complete(messages) trả JSON text hoặc dict, không trả SDK envelope.
# Bộ gọi provider tự cấu hình model, secret, timeout và giới hạn đầu ra.
generate = make_guarded_generator(complete)
# Dependency research_callbacks của backend trả (assess, generate).
# assess là bộ đánh giá căn cứ riêng do server cấu hình, không phải hàm
# luôn trả sufficient=True và không nhận phê duyệt từ request của client.
```

Chỉ gọi generator qua guardrails. Thiếu dữ kiện, thiếu assessor hoặc nguồn bị
từ chối thì không gọi model. Lỗi provider đi qua ranh giới lỗi đã che của An.
Prompt không cấp quyền, không thẩm định luật và không thay thế bộ đánh giá căn cứ.
Chưa sửa dependency `research_callbacks`: ứng dụng vẫn không gọi provider thật.

Phước cần dùng các khóa sáu phần ở trên khi đặt tiêu đề trên giao diện; kết quả
`clarify/abstain` có sáu mảng rỗng, câu hỏi nằm trong `clarification_questions`,
lý do/giới hạn trong `warnings`. Metadata audit do server quản lý, model không trả.

## Kiểm chứng

Chạy từ gốc repository với dependencies backend:

```powershell
python -m pytest tests/guardrails/test_prompt_integration.py -q
```

Các ca dùng nguồn và provider giả lập: giữ dữ kiện đã che, chỉ gửi nguồn được
chấp nhận, draft đi tới exporter Word, clarify/abstain, chặn ID ngoài tập nguồn,
approved/JSON sai, lỗi provider và không gọi model khi thiếu căn cứ/dữ kiện.
Test được pytest hiện tại thu thập trong `tests/guardrails`.

Kết quả ngày 20/11: toàn bộ bộ test trên nhánh này đạt **223 passed, 1 skipped**
với SQLite riêng; 16 ca mới thuộc phần prompt. Test bị bỏ qua là migration SQL
chỉ dành cho PostgreSQL. `git diff --check` đạt. Chưa xác nhận migration bằng
lần chạy SQLite này hoặc khả năng tích hợp với các nhánh chưa gộp.

Đây là kiểm chứng kỹ thuật, không đo chất lượng model hay tính đúng pháp lý.
Trước nghiệm thu cần chạy model được cấu hình trên bộ câu hỏi/nguồn đã đối chiếu,
ghi phiên bản prompt/model và kết quả chuyên gia; không biến kết quả giả lập
thành nhãn căn cứ đủ cho luật thật.
