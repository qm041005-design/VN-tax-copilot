# SCRUM-24 — sửa tích hợp backend

Ngày 14/11/2026. Nhánh `codex/scrum-24-backend-fixes`, dựa trên backend `df45332`, guardrails An `8083a0e` và BM25 Thanh `28f9c8a`. Đây là code sửa bổ sung, không phải chứng nhận nghiệm thu doanh nghiệp.

## Hành vi đã thay đổi

- Khoản lưu String(20), giữ `1a`. Cả số 0, chuỗi "0", rỗng và null đều trả `khoan=null`, kể cả adapter guardrails.
- Tìm kiếm xếp theo BM25 trên tập ứng viên đã lọc, thay SQL đếm từ. Thứ hạng không phải thứ bậc pháp lý. Hiện tạo chỉ mục trong mỗi request: chỉ dành pilot nhỏ, chưa chứng minh tải 10.000 tài liệu.
- Lọc sắc thuế theo bảng `legal_document_tax_scopes(doc_id, tax_type)`, nhãn do người nhập dữ liệu xác minh. Một văn bản có nhiều nhãn. Khi có bộ lọc, văn bản chưa gán nhãn bị loại; không đoán loại từ tiêu đề hoặc câu hỏi. Duyên/Thanh cần nạp nhãn cho dữ liệu thật. Bảng mới độc lập, không tự thay schema tài liệu của Duyên.
- `tax_period`: nhận YYYY, YYYY-MM, YYYY-Q1..Q4. Kỳ không hiểu trả 422, không tự đoán. Kế thừa kỳ hồ sơ khi request không cung cấp.
- Nếu có kỳ thuế, chọn văn bản có khoảng hiệu lực giao với kỳ đó, không lấy research_as_of làm ngày áp dụng. Nếu không có kỳ, as_of dùng để tìm ứng viên tại một ngày. expiry_date là mốc kết thúc không bao gồm ngày đó. Ngày hiệu lực/expiry thiếu vẫn là ứng viên chưa xác minh.
- Đây là lọc ứng viên ở cấp văn bản, không giải quyết hồi tố, chuyển tiếp hoặc sửa đổi từng khoản. Không tự xác nhận đủ căn cứ bằng bộ lọc này. research_as_of vẫn lưu mốc nghiên cứu; hệ thống chưa tái tạo kho nguồn đúng trạng thái tri thức của một ngày trong quá khứ.
- `/research` gọi guardrails sau kiểm tra quyền hồ sơ. Không có assessor/generator thì clarify/abstain, không gọi API AI trả phí. Callback được cấp trên server qua dependency research_callbacks, không nhận từ client.
- Có `research_result` ở cấp response với status và sáu phần. `history.answer` là nội dung đã qua kiểm tra nếu có. Trạng thái/giải thích được lưu warnings. Chưa lưu object sáu phần vào database: tải lịch sử chưa khôi phục nguyên object này, phần xuất Word cuối luồng vẫn cần tích hợp tiếp.
- Khi answer=null, history.citations vẫn lưu nguồn ứng viên để giao diện cũ mở lại được; không được hiển thị là trích dẫn đã kiểm chứng. Khi draft có câu trả lời, chỉ lưu citation_ids được guardrails chấp nhận.
- Câu hỏi và tình tiết được che bằng bộ redaction hiện có trước khi lưu lịch sử; bộ này chưa bao phủ mọi loại thông tin cá nhân.

## Chạy trên máy

Từ gốc repository, cài `python -m pip install -r backend/requirements.txt`, rồi `python -m pytest -q`. pytest.ini bổ sung cả root và backend vào đường dẫn import.

Chạy API (PowerShell), sau khi cấu hình DATABASE_URL và AUTH_TOKENS cho môi trường thử nghiệm:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\backend"
python -m uvicorn app.main:app --app-dir backend --reload
```

Nếu dùng backend/.env, chạy từ thư mục backend sau khi đặt PYTHONPATH ở gốc. Không đưa token thật vào mã nguồn. Giao diện thử nghiệm cần token khớp backend; không dùng token công khai chung cho môi trường doanh nghiệp.

## Database đang tồn tại

`create_all()` không đổi kiểu cột cũ. Với PostgreSQL đã có dữ liệu, sao lưu, dừng writer, áp dụng `backend/migrations/001_clause_number_text.sql`, rồi kiểm tra dữ liệu cũ và mới. SQL dùng transaction, đổi kiểu bằng CAST và tạo bảng nhãn nếu chưa có. Không tự chạy migration trên database người dùng; không drop dữ liệu để nâng cấp.

SQLite trong test được tạo mới hoàn toàn. File SQLite ứng dụng đang dùng cần kế hoạch chuyển đổi riêng; migration trên là PostgreSQL-only. SQL migration chưa chạy trên PostgreSQL trong môi trường này vì Docker daemon chưa bật.

Phối hợp Duyên: kiểu clause_number mới tương thích String(20); các trường mới khác của registry và quan hệ sửa đổi vẫn cần thống nhất migration chung. Nguồn chưa có nhãn sắc thuế phải được phân loại trước khi bật bộ lọc để tránh tưởng rằng kho không có văn bản.

## Docker và Phúc

Backend Docker build context đổi thành gốc repo, Dockerfile là backend/Dockerfile để copy cả backend và ai_engine. Không dùng `docker build backend` nữa; dùng `docker build -f backend/Dockerfile .`. Root .dockerignore loại file bí mật, database và môi trường local. Compose giữ AUTH_TOKENS/CORS và đồng bộ DATABASE_URL với POSTGRES_*.

Phúc cần giữ các thay đổi này khi ghép PR Docker/CI. Frontend chưa nằm trên nhánh sửa backend này; Compose đầy đủ còn phụ thuộc nhánh frontend. Docker build và PostgreSQL thực tế chưa được kiểm chứng ở đây.

## Bằng chứng và giới hạn

- 101 test đạt: backend cũ + hồi quy kỳ thuế lịch sử/sắc thuế/Khoản 1a/guardrails qua HTTP, 45 test guardrails và 3 test BM25.
- Test backend dùng SQLite riêng và provider giả lập, không tư vấn pháp lý, không gọi LLM thật.
- Test giả lập assessor chỉ dùng để kiểm tra việc chặn/cho phép và ID trích dẫn. Sản phẩm vẫn mặc định chưa cấu hình assessor.
- Chưa đo tải pilot, chưa nghiệm thu chuyên môn, chưa xác nhận Docker/PostgreSQL hay frontend end-to-end.

Các hướng dẫn SCRUM-23 về áp dụng patch endpoint chỉ dành backend cũ: nhánh này đã tích hợp endpoint, không áp dụng patch lần nữa.
