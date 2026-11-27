# Hướng dẫn test backend

Làm lần lượt từ bước 1 đến bước 7, mỗi bước có **"Đúng khi"** để tự đối chiếu.
Mọi lệnh gõ trong PowerShell, bắt đầu ở thư mục gốc repo `VN-tax-copilot`.

## Dẫn chứng hoàn thành task Jira SCRUM-33

Mỗi task có **test tự động** (chạy ở bước 6) và **bước kiểm tra tay** (bước 3–5) chứng minh đã xong.

| Task SCRUM-33 | Trạng thái | Test tự động chứng minh | Kiểm tra tay |
|---|---|---|---|
| 1. Hoàn tất review `f3fa3a2` (migration + hiệu lực) | ✅ Đã sửa, chờ Quân xác nhận | `test_migrations.py::test_migration_nang_cap_db_cu_khong_mat_du_lieu` (DB cũ nâng cấp qua 001→004, không mất dữ liệu)<br>`test_sources_research.py::test_doan_luat_hieu_luc_rieng_nam_2030_khong_hien_khi_tra_cuu_2026` (lọc ngày hiệu lực của từng đoạn) | Mục "Gặp lỗi": 4 lệnh migration |
| 2. Phối hợp Duyên (importer), An (metadata guardrails) | ✅ Phần Duyên: backend nhận đủ metadata mới. Phần An: đã review, An tự nối metadata cấp đoạn (nhánh SCRUM-32) | `test_data_pipeline_sync.py` (model backend khớp từng cột với registry của Duyên)<br>`test_ocr_review_status.py` (importer lưu `preamble`, trạng thái OCR, trạng thái duyệt; không nhận phê duyệt qua file nạp)<br>`test_migrations.py` (migration 004)<br>`test_legal_ingestion.py` (kiểm tra dữ liệu, không ghi đè, rollback khi lỗi) | Bước 2: nạp luật qua importer |
| 3. Lưu kết quả 6 phần vào lịch sử, trả lại khi mở hồ sơ | ✅ | `test_research_export.py::test_ket_qua_6_phan_duoc_luu_va_tra_lai_khi_mo_ho_so`<br>`test_research_export.py::test_luot_tra_cuu_cu_khong_co_ket_qua_6_phan` | Bước 3, dòng 4 (F5 vẫn còn) |
| 4. Endpoint xuất Word nối module Quân, kiểm tra quyền trước khi xuất | ✅ (backend) | `test_research_export.py::test_xuat_word` (ra file .docx đủ 6 phần + audit)<br>`::test_xuat_word_kiem_tra_quyen_truoc` (401, 404 tổ chức khác, 404 sai hồ sơ, không ghi audit)<br>`::test_xuat_word_khi_nguon_bi_xoa` (409)<br>`::test_xuat_word_khi_nguon_khong_co_link` (422)<br>`test_cors.py::test_actual_response_carries_cors_headers_and_exposes_total_count` (frontend đọc được tên file) | Bước 4 và 5 |
| 5. Cập nhật API contract, test, mô tả PR | ✅ | Toàn bộ bộ test (bước 6) | `API_CONTRACT.md`, file này, mô tả PR |

### SCRUM-36 (tuần 26/11)

| Task SCRUM-36 | Trạng thái | Test tự động chứng minh |
|---|---|---|
| 1. Tích hợp backend với parser/registry, BM25, guardrails, prompt mới | ✅ phần backend (BM25 SCRUM-31 của Thanh chờ merge) | `test_ai_integration.py::test_tra_cuu_ra_ban_nhap_6_phan_luu_lich_su_va_xuat_word` (registry → BM25 → guardrails → prompt tuần 4 → lưu lịch sử → Word, model giả)<br>`::test_thieu_tinh_tiet_thi_khong_goi_model`<br>`::test_doc_cau_hinh_module_ham`<br>`tests/guardrails/test_prompt_integration.py` (của Quân), `test_scrum32.py` (của An) |
| 2. Giữ đầy đủ metadata khi nạp; thống nhất importer với Duyên, Thanh | ✅ (trừ `status` pháp lý – chờ chốt) | `test_ocr_review_status.py::test_moi_cot_metadata_trong_model_deu_duoc_luu` (mọi cột model đều được lưu; importer cũ thì test fail)<br>`test_data_pipeline_sync.py` (khớp registry của Duyên)<br>`test_legal_ingestion.py` (dùng chung quy tắc importer với SCRUM-31 của Thanh) |
| 3. Kiểm tra lưu và mở lại kết quả 6 phần | ✅ API + giao diện | `test_ai_integration.py::test_ca_3_trang_thai_deu_luu_va_mo_lai_dung` (draft / clarify / abstain)<br>Giao diện (frontend trên `main`): mở lại hồ sơ hiện đủ trạng thái, 6 mục, câu hỏi bổ sung, cảnh báo |
| 4. Kiểm tra API xuất Word và quyền; hỗ trợ Phước | ✅ backend; bản sửa nút cho Phước đã chạy thử | `test_research_export.py` (401/404/409/422, audit, hồ sơ lưu trữ vẫn xuất được)<br>`test_ai_integration.py` (Word có nội dung bản nháp AI)<br>Giao diện: nút "Xuất báo cáo" gọi API → 200, tải `.docx`; lượt cũ → hiện thông báo 409 tiếng Việt |

Ngoài phạm vi backend: nút "Xuất báo cáo" trên giao diện chưa gọi API Word (việc của frontend).

---

## Bước 0 – Cài đặt (chỉ làm lần đầu)

```powershell
copy .env.example .env
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
cd ..\frontend
npm ci
Set-Content -Encoding ascii .env.local "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`nNEXT_PUBLIC_DEV_API_TOKEN=dev-token-alice-0001"
cd ..
```

## Bước 1 – Bật hệ thống

Mở **Docker Desktop**, đợi chữ *Running*. Sau đó mở 3 terminal:

**Terminal 1 – Database**
```powershell
docker compose up -d db
```

**Terminal 2 – Backend**
```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = ".."
python -m uvicorn app.main:app --reload
```

**Terminal 3 – Frontend**
```powershell
cd frontend
npm run dev
```

Đúng khi: http://localhost:8000/health có `"database": true` và http://localhost:3000 hiện danh sách hồ sơ.

> ⚠️ **Đã có DB từ trước** (máy đã chạy backend bản cũ) mà vừa `git pull`: chạy 4 lệnh migration ở cuối file **một lần** trước khi test. Không chạy thì tra cứu báo lỗi `column ... does not exist`. Máy mới tạo DB lần đầu thì không cần.

## Bước 2 – Nạp luật mẫu ⚠️ đừng bỏ qua

> Bỏ bước này thì kho luật trống, hỏi gì cũng ra **"Không tìm thấy căn cứ pháp lý phù hợp"**.

Mở thêm 1 terminal, copy nguyên khối dưới:

```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = ".."
@'
{"document": {"doc_code": "MAU-48/2024/QH15", "title": "Luật Thuế GTGT (mẫu)", "doc_type": "LUAT",
  "hierarchy_level": 1, "effective_date": "2025-07-01", "source_url": "https://vbpl.vn/mau-48-2024"},
 "chunks": [{"article_number": "9", "article_title": "Thuế suất", "clause_number": "3",
  "citation_path": "Khoản 3, Điều 9, MAU-48/2024/QH15", "hierarchy_level": 1,
  "content": "Khoản 3, Điều 9: Mức thuế suất 10% áp dụng đối với hàng hóa, dịch vụ không thuộc diện 0% và 5% (nội dung mẫu)."}],
 "tax_types": ["VAT"], "as_of": "2026-11-19"}
'@ | Set-Content -Encoding utf8 mau.json
python -m scripts.import_legal_document --input mau.json
```

Đúng khi: in ra dòng bắt đầu bằng `{"document_id": ...`.
Báo `Mã văn bản đã tồn tại` → đã nạp từ trước, bỏ qua và làm tiếp.

## Bước 3 – Test trên giao diện (http://localhost:3000)

| # | Làm gì | Đúng khi |
|---|---|---|
| 1 | Chọn 1 hồ sơ có nhãn **VAT** (hoặc tạo mới, chọn sắc thuế VAT) | Hồ sơ mở ra |
| 2 | Hỏi: `Mức thuế suất 10% áp dụng cho hàng hóa nào?` | Có khung **"Căn cứ từ API"** ghi `Khoản 3, Điều 9, MAU-48/2024/QH15`; dưới cùng báo "Đã lưu lượt tra cứu vào hồ sơ" |
| 3 | Bấm vào trích dẫn đó | Cột phải hiện: LUAT, MAU-48/2024/QH15, hiệu lực từ 2025-07-01, VAT, "Mở nguồn" |
| 4 | Bấm **F5**, chọn lại hồ sơ | Câu hỏi + trích dẫn **vẫn còn** |
| 5 | Ô "Tìm văn bản pháp luật", gõ `thuế suất` | Ra đoạn Khoản 3, Điều 9 |
| 6 | Chuyển sang hồ sơ khác rồi quay lại | Mỗi hồ sơ chỉ có lịch sử của nó |

**Những thứ trông giống lỗi nhưng KHÔNG phải lỗi backend:**
- "Backend chưa cung cấp câu trả lời AI" + `clarify: missing_context` → chưa nối AI, đúng thiết kế.
- Hỏi bằng tên trích dẫn (vd `Khoản 3, Điều 9, ...`) → nên hỏi bằng câu hỏi tự nhiên như dòng 2.
- Nút "Xuất báo cáo", "Phê duyệt" trên giao diện → việc của frontend (nhóm 9), backend test qua Swagger ở bước 4.

## Bước 4 – Xuất Word (Swagger http://localhost:8000/docs)

1. Bấm **Authorize** (ổ khóa góc phải) → nhập `dev-token-alice-0001` → Authorize.
2. Lấy 2 ID của lượt vừa tra cứu – cách nhanh nhất, chạy ở thư mục gốc:
   ```powershell
   docker compose exec -T db psql -U vntax_admin -d vntax_copilot -c "select matter_id, id as history_id, left(question,40) from research_history where citations::text <> '[]' order by created_at desc limit 3;"
   ```
   (Hoặc trong Swagger: `GET /matters` lấy `id` hồ sơ → `GET /matters/{id}/history` lấy `id` lượt tra cứu.)
3. Mở `GET /matters/{matter_id}/history/{history_id}/export` → **Try it out** → dán 2 ID → **Execute**.

Đúng khi: Code **200**, có link **Download file**, file `.docx` mở ra có "DỰ THẢO – CHƯA ĐƯỢC CHUYÊN GIA PHÊ DUYỆT" và 6 phần.

> Swagger báo *"Required field is not provided / Value must be a Guid"* → chưa dán ID vào 2 ô.
> Chọn lượt **không có trích dẫn** thì file Word gần như trống – hãy chọn lượt có trích dẫn.

## Bước 5 – Phân quyền (vẫn ở API export, giữ 2 ID)

| Làm gì | Đúng khi |
|---|---|
| Ổ khóa → **Logout** → Execute | **401** |
| **Authorize** bằng `dev-token-bob-0002` → Execute | **404** (bob không thấy hồ sơ của alice) |
| Authorize lại alice, đổi `history_id` thành ID của lượt ở **hồ sơ khác** → Execute | **404** |
| Chọn lượt có trích dẫn tới văn bản **đã bị xóa** khỏi kho → Execute | **409** "Nguồn luật được trích dẫn không còn trong kho" |
| Tạo hồ sơ thử → `DELETE /matters/{id}` → hỏi tiếp trên hồ sơ đó | **409** (hồ sơ đã lưu trữ chỉ được xem) |

## Bước 6 – Test tự động

```powershell
cd backend
$env:PYTHONPATH = ".."
$env:TEST_DATABASE_URL = "postgresql://vntax_admin:vntax_secret@localhost:5432/vntax_test"
python -m pytest -q
```

Đúng khi: `113 passed` trên PostgreSQL. Không đặt `TEST_DATABASE_URL` thì chạy trên SQLite: `112 passed, 1 skipped` (test migration chỉ chạy trên PostgreSQL).
Lần đầu chưa có DB test: `docker compose exec db psql -U vntax_admin -d vntax_copilot -c "CREATE DATABASE vntax_test"`.
⚠️ **Không** trỏ `TEST_DATABASE_URL` vào `vntax_copilot` – test xóa sạch bảng.

## Bước 7 – Dọn dẹp

```powershell
docker compose exec db psql -U vntax_admin -d vntax_copilot -c "DELETE FROM legal_document_tax_scopes WHERE doc_id IN (SELECT id FROM legal_documents WHERE doc_code='MAU-48/2024/QH15'); DELETE FROM legal_chunks WHERE doc_id IN (SELECT id FROM legal_documents WHERE doc_code='MAU-48/2024/QH15'); DELETE FROM legal_documents WHERE doc_code='MAU-48/2024/QH15';"
del backend\mau.json
```

Tắt backend/frontend: `Ctrl+C`. Tắt DB: `docker compose stop`.

---

## Gặp lỗi thì xem đây

| Thấy gì | Nguyên nhân → Cách sửa |
|---|---|
| Hỏi gì cũng "Không tìm thấy căn cứ pháp lý phù hợp" | Chưa nạp luật → làm **bước 2**; hoặc hồ sơ không có nhãn VAT |
| Giao diện "Failed to fetch" | Backend chưa chạy → terminal 2 |
| Mọi API trả 401 | Thiếu `AUTH_TOKENS` trong `backend\.env` hoặc thiếu `frontend\.env.local` → bước 0 |
| `No module named 'ai_engine'` hoặc `'app'` | Chưa gõ `$env:PYTHONPATH = ".."`, hoặc không đứng trong thư mục `backend` |
| `docker compose` báo thiếu `POSTGRES_USER` | Chưa có `.env` ở thư mục gốc → bước 0 |
| Lỗi kết nối Docker / `dockerDesktopLinuxEngine` | Docker Desktop chưa bật |
| `column ... does not exist` | DB tạo từ bản cũ → chạy 4 lệnh migration bên dưới |

Migration (từ thư mục gốc, chạy lại nhiều lần vẫn an toàn, không mất dữ liệu):
```powershell
Get-Content backend\migrations\001_clause_number_text.sql | docker compose exec -T db psql -U vntax_admin -d vntax_copilot
Get-Content backend\migrations\002_legal_status_and_registry_columns.sql | docker compose exec -T db psql -U vntax_admin -d vntax_copilot
Get-Content backend\migrations\003_research_result.sql | docker compose exec -T db psql -U vntax_admin -d vntax_copilot
Get-Content backend\migrations\004_ocr_and_expert_review_status.sql | docker compose exec -T db psql -U vntax_admin -d vntax_copilot
```
