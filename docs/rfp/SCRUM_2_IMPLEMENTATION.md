# SCRUM-2 Prompt và xuất Word

`ai_engine/synthesis/prompt_templates.py` cung cấp `SYSTEM_PROMPT`, `SECTION_LABELS`
và `build_messages(question, passages, ...)`. Không cần khóa API để tạo messages.
Caller chỉ truyền đoạn nguồn đã được cấp quyền cho user/matter hiện tại.
Các metadata của passage cần chứa số văn bản, Điều/Khoản/Điểm nếu có, phiên bản,
ngày hiệu lực, kỳ áp dụng và URL nguồn. Thiếu dữ kiện được giữ là chưa rõ.

Kết quả mô hình có `status` (draft/clarify/abstain), `sections` gồm sáu khóa
issue/facts/authority/analysis/limitations/next_steps. Mỗi phần là danh sách
`{"text": "...", "citation_ids": ["passage_id"]}`; hai danh sách bổ sung là
`clarification_questions` và `warnings`.

`backend/app/services/export_service.py` cung cấp
`export_research_docx(result, sources, title=..., matter_id=...) -> bytes`.
`sources` là dictionary khóa passage_id, metadata gồm document_number, article,
source_url và tùy chọn clause, point, version_note. Backend xây dựng mapping này
từ registry đáng tin cậy, không lấy URL do mô hình tự sinh. Bytes có thể trả qua
HTTP với MIME application/vnd.openxmlformats-officedocument.wordprocessingml.document.
Chạy từ gốc monorepo để import được cả backend và ai_engine.

Word có header THTax, sáu phần, số nguồn và hyperlink, đồng thời giữ trạng thái
dự thảo. Không có template/logo chính thức được cung cấp nên header là chữ THTax.
Hàm từ chối citation không tồn tại, URL ngoài HTTP(S), thiếu trích dẫn trong căn cứ
hoặc phân tích của draft và trạng thái approved do caller truyền vào.

```powershell
python -m pip install -r backend/requirements.txt
python -m unittest evaluation.test_scrum2 -v
```

Đã có kiểm tra cấu trúc DOCX, nội dung tiếng Việt, header, quan hệ hyperlink và
các đường lỗi quan trọng. Chưa kiểm tra bố cục bằng Word/LibreOffice hoặc gọi
mô hình thật. Prompt không bảo đảm tuyệt đối chống prompt injection hay bịa đặt;
validator kiểm tra hỗ trợ claim/passage, kiểm soát quyền matter, phê duyệt chuyên
gia và API tải xuống là các điểm tích hợp tiếp theo của nhóm phụ trách tương ứng.
