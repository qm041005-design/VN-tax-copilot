# SCRUM-23 — Tích hợp bảo vệ dữ liệu và kiểm tra trích dẫn

## Đã triển khai

- `run_guarded_research`: hỏi bổ sung kỳ thuế/tình huống trước mọi lời gọi AI.
- Che câu hỏi, tình huống, kỳ thuế và toàn bộ nội dung nguồn trước assessor/generator.
- Không cho sinh khi thiếu nguồn, chưa có assessor hoặc assessor chưa xác nhận đủ căn cứ.
- Chỉ truyền nguồn đã chọn cho generator; kiểm tra từng claim có citation ID trong đúng tập này.
- Dựng answer từ các claim đã kiểm tra; không phát hành free-text chưa kiểm tra.
- Che dữ liệu trong đầu ra và không trả lỗi provider chứa prompt/dữ liệu thô.
- Adapter `backend/app/services/guarded_research_service.py` nhận rows từ source_service, dùng full content và ID database.

## Chạy test

Python 3.10+, không cần API key hay package ngoài cho bộ guardrails:

```powershell
python -m unittest discover -s tests/guardrails -v
```

Kết quả kiểm tra: 45 test đạt (13 test cũ + 32 test mới). Test dùng callback giả lập, không gọi LLM thật.

## Áp dụng endpoint khi Backend đã được tích hợp

Bản vá dựa trên `feature/08-backend-matter-services` commit `df453329bafee6b884adc8fe922e03e9e162733e`.
Không áp dụng khi chưa có file endpoint của Backend. Từ gốc repo:

```powershell
git apply --check docs/integration/SCRUM-23-backend-route.patch
git apply docs/integration/SCRUM-23-backend-route.patch
```

Giữ kiểm tra quyền hồ sơ trước pipeline. Warnings lưu trạng thái và câu hỏi bổ sung vào response hiện có, không đổi schema. History question/material_facts được che. `sources` và `history.citations` trong endpoint hiện tại vẫn là các nguồn tìm được, KHÔNG phải xác nhận hỗ trợ kết luận. Khi nối generator thật, nhóm Backend cần lưu citations của answer chỉ theo `result.citation_ids`; lấy metadata từ server, không tin metadata AI trả về.

Chạy Backend từ gốc repo với root có trên PYTHONPATH, ví dụ:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\backend"
python -m uvicorn app.main:app --reload
```

Docker hiện có của Backend cần copy cả `ai_engine` vào image và thêm root vào PYTHONPATH; phối hợp Tech Lead sửa build context. Không đưa callback từ request body. Trong server truyền `assess=` và `generate=` vào `research_from_rows`; cả hai nhận `SafeResearchInput`. Assessor trả list `EvidenceAssessment`; generator trả `GeneratedResearch` chứa các `Claim` có `citation_ids`.

## Giới hạn và phần phối hợp

Bản vá endpoint đã kiểm tra áp dụng trên đúng commit Backend và kiểm tra cú pháp; chưa chạy API/database integration tests. Pipeline và adapter đã được unit test. Backend chưa có LLM/assessor thật, nên mặc định từ chối sinh. Cờ sufficient yêu cầu assessor thực sự kiểm tra mức liên quan, hiệu lực, mâu thuẫn và mức đủ thông tin. Không bật True cho mọi hit hoặc lấy cờ từ client.

Kiểm tra citation ID không chứng minh claim đúng hay trích dẫn nguyên văn đúng. Claim có thể chứa số hiệu luật viết sai trong text; cần Citation Validator ngữ nghĩa và chuyên gia duyệt tiếp. Không có cơ chế tự suy ra kỳ thuế từ câu hỏi: endpoint lấy tax_period từ request hoặc hồ sơ; thiếu thì hỏi lại. Các trường có giá trị nhưng quá mơ hồ vẫn cần assessor đánh giá. Với câu hỏi định nghĩa không phụ thuộc kỳ thuế, server có thể dùng policy `ResearchContext(require_tax_period=False, require_material_facts=False)`.

Regex kế thừa SCRUM-11 còn có giới hạn với tên, địa chỉ, bảng lương và số viết cách nhóm. Không bật logging prompt hay lỗi provider thô. Metadata nguồn phục vụ UI chưa được coi là dữ liệu đưa ra LLM.

## Commit từ máy của An

Dùng nhánh số 7 hiện có; nếu PR #7 chưa merge, commit này cập nhật cùng PR. Nếu nhóm muốn PR SCRUM-23 riêng, tạo nhánh riêng và thống nhất base với trưởng nhóm vì SCRUM-11 chưa có trên develop tại thời điểm kiểm tra.

```powershell
git status
git fetch origin
git switch feature/07-ai-grounding-citations
git pull --ff-only origin feature/07-ai-grounding-citations
# Chép nội dung thư mục code trong ZIP vào gốc repo, rồi chạy test.
git config user.name "Nguyễn Quốc An"
git config user.email "quocan3004@gmail.com"
git add ai_engine/guardrails backend/app/services/guarded_research_service.py tests/guardrails docs/integration
git diff --cached --stat
git commit -m "feat(SCRUM-23): integrate research guardrails and citation checks"
git -c credential.username=ansocute push origin feature/07-ai-grounding-citations
```

Không cần force push. Nếu git status có thay đổi đang làm dở hoặc pull báo xung đột, dừng và xử lý trước khi chép code.


## Cập nhật v2 — thay gói ZIP cũ

- Thống nhất status: `draft`, `clarify`, `abstain`; lỗi provider cũng trả abstain với reason riêng.
- `to_contract(result)` trả đủ sáu phần: issue, facts, authority, analysis, limitations, next_steps; kèm clarification_questions và warnings.
- Generator nhận dữ liệu đã che và có thể trả JSON string hoặc dict theo prompt của Quân. Dùng `make_prompt_generator(build_messages, complete)` để nối hàm prompt với LLM provider của server.
- Với draft, authority và analysis phải có nội dung và mỗi mục có citation_ids. Mã trích dẫn phải thuộc nguồn đã được assessor chọn. Mọi citation ở các phần khác cũng được kiểm tra.
- Các phần khác cho phép thông tin sự kiện/hướng dẫn không trích dẫn; bộ kiểm tra cấu trúc không tự phát hiện mọi khẳng định pháp lý bị đặt sai phần. Cần validator ngữ nghĩa/chuyên gia kiểm tra tiếp.
- Clarify/abstain do provider trả sẽ không phát hành nội dung kết luận. clarify cần ít nhất một câu hỏi bổ sung.
- Cho phép metadata scalar đã che: dieu/khoan/diem/doc_type/effective_date/expiry_date/version/source_page; URL và metadata khác giữ phía server. Khoản 0/điểm rỗng được adapter chuyển null. Toàn văn không bị cắt thành snippet.
- Kết quả kiểm tra bổ sung: hàm `build_messages` thực tế của Quân tại a886063 hoạt động cùng pipeline và phản hồi provider giả lập. Chưa gọi LLM thật, chưa kiểm thử API/database, chưa kiểm thử xuất Word cuối luồng.
- Tài liệu tuần 3 của Quân vẫn là đề xuất chờ nhóm xác nhận. Adapter theo đề xuất hiện tại, không tự đổi API schema hoặc đặt trạng thái chuyên gia approved.

Demo minh chứng (chỉ fixture, không phải đánh giá dữ liệu luật thật):

```powershell
python -m ai_engine.guardrails.demo_scrum23
```

Kết quả theo thứ tự: clarify / abstain / draft / abstain. Fixture sufficient=True chỉ để test, không dùng làm assessor cho sản phẩm.

Hướng dẫn chụp: ảnh 45 tests OK; ảnh demo bốn trạng thái; ảnh code research.py/contract.py; ảnh commit do tài khoản ansocute tạo. Chỉ chuyển Jira sang In Review khi đã tạo PR và mô tả rõ giới hạn tích hợp.
