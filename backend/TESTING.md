> **Cập nhật SCRUM-24 (14/11/2026):** xem [hướng dẫn tích hợp mới](SCRUM_24_FIXES.md) trước các lệnh bên dưới; backend hiện phụ thuộc ai_engine ở gốc repo, dùng migration cho DB cũ và Docker build context ở gốc.

# 🧪 TESTING – Hướng dẫn kiểm thử Backend

> **3 điều cần biết trước**
> 1. Test nằm trong thư mục `backend/tests/` (có trên nhánh `feature/08-backend-matter-services`, và trên `develop` sau khi PR backend được merge).
> 2. Test dùng database **riêng** tên `vntax_test` – test xóa sạch bảng mỗi lần chạy, nên **không bao giờ** trỏ test vào `vntax_copilot`.
> 3. Luôn gõ `python -m pytest` và `python -m uvicorn` (có `python -m` phía trước).

Mọi lệnh gõ trong **terminal PowerShell của VS Code** (`Terminal → New Terminal`).

---

## BƯỚC 1 – Chuẩn bị

### 1a. Lần đầu tiên trên máy (chỉ làm một lần)
Đứng ở thư mục gốc repo `VN-tax-copilot`:
```powershell
git switch feature/08-backend-matter-services
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
cd ..
```

### 1b. Mỗi lần mở máy để test
Mở **Docker Desktop**, đợi báo *Running*, rồi đứng ở thư mục gốc `VN-tax-copilot`:
```powershell
git switch feature/08-backend-matter-services
docker compose up -d db
docker exec vn_tax_db psql -U vntax_admin -d vntax_copilot -c "CREATE DATABASE vntax_test"
cd backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```
✅ Đạt khi: dòng lệnh có dạng `(.venv) PS ...\VN-tax-copilot\backend>` – có `(.venv)` ở đầu **và** kết thúc bằng `\backend>`.
(Dòng `CREATE DATABASE` báo `already exists` là bình thường.)

> ⚠️ **Mọi lệnh ở Bước 2 đều chạy trong thư mục `backend`.** Nếu dòng lệnh kết thúc bằng `\VN-tax-copilot>` thì gõ `cd backend` trước.

---

## BƯỚC 2 – Kiểm chứng 4 nhiệm vụ

### ✅ Nhiệm vụ 1: Kiểm thử API hồ sơ trên PostgreSQL thật

**Làm:** chạy toàn bộ test, trỏ vào Postgres.
```powershell
$env:TEST_DATABASE_URL="postgresql://vntax_admin:vntax_secret@localhost:5432/vntax_test"
python -m pytest -v
```
**Đạt khi:** dòng cuối là `37 passed`.

**Chứng minh đúng là Postgres (không phải SQLite):** tắt DB rồi chạy lại.
```powershell
docker compose stop db
python -m pytest -q
```
**Đạt khi:** test **báo lỗi hàng loạt** (không kết nối được DB). Bật lại:
```powershell
docker compose start db
python -m pytest -q
```
**Đạt khi:** lại `37 passed`.

Xong nhiệm vụ 1 thì gỡ biến: `Remove-Item Env:TEST_DATABASE_URL`

---

### ✅ Nhiệm vụ 2: API tìm kiếm, xem nguồn, lưu lịch sử theo hồ sơ

**2.1 – Test tự động**
```powershell
python -m pytest tests/ -v -k "search or source or research"
```
**Đạt khi:** tất cả dòng đều `PASSED`.

**2.2 – Test tay**

① Chạy server (terminal này để nguyên):
```powershell
python -m uvicorn app.main:app --reload
```
② Mở **terminal thứ 2** (nút **+** trên khung terminal), nạp **1 đoạn luật demo** (nội dung tự đặt, không phải luật thật):
```powershell
docker exec vn_tax_db psql -U vntax_admin -d vntax_copilot -c "INSERT INTO legal_documents (doc_code,title,doc_type,hierarchy_level,version,effective_date) VALUES ('DEMO-01','Văn bản mẫu (demo)','LUAT',1,'1.0','2025-07-01'); INSERT INTO legal_chunks (doc_id,article_number,clause_number,point_letter,citation_path,content,hierarchy_level) SELECT id,'9',3,'a','Điểm a, Khoản 3, Điều 9, DEMO-01','Thuế suất 10% là mức phổ thông (nội dung demo).',1 FROM legal_documents WHERE doc_code='DEMO-01';"
```
③ Mở trình duyệt http://localhost:8000/docs → bấm **Authorize** (góc phải) → dán `dev-token-alice-0001` → **Authorize** → **Close**.

④ Với mỗi dòng dưới: bấm vào endpoint → **Try it out** → nhập → **Execute**.

| # | Endpoint | Nhập | Đạt khi |
|---|---|---|---|
| 1 | `POST /api/v1/matters` | `{"title":"Thử VAT","client_name":"ABC","tax_types":["VAT"],"tax_period":"2026"}` | Mã **201**. **Copy giá trị `id`** (gọi là ID_HS) |
| 2 | `GET /api/v1/sources/search` | ô `q`: `phổ thông` | Có 1 kết quả, `legal_identifier` = `DEMO-01`. **Copy `source_id`** |
| 3 | `GET /api/v1/sources/search` | ô `q`: `phổ thông`, ô `as_of`: `2020-01-01` | Trả `[]` (năm 2020 văn bản chưa có hiệu lực) |
| 4 | `GET /api/v1/sources/{source_id}` | source_id ở bước 2 | Có trường `content` = nguyên văn đoạn luật |
| 5 | `POST /api/v1/research` | `{"matter_id":"ID_HS","question":"thuế suất phổ thông"}` | Mã **201**, `sources` có 1 phần tử |
| 6 | `GET /api/v1/matters/{matter_id}/history` | ID_HS | Thấy câu hỏi "thuế suất phổ thông" vừa gửi |

⑤ Kiểm tra dữ liệu đã nằm trong Postgres (ở terminal thứ 2):
```powershell
docker exec vn_tax_db psql -U vntax_admin -d vntax_copilot -c "SELECT question FROM research_history ORDER BY created_at DESC LIMIT 1;"
```
**Đạt khi:** in ra `thuế suất phổ thông`.

---

### ✅ Nhiệm vụ 4: Xác thực tối thiểu + quyền truy cập hồ sơ

**4.1 – Test tự động** (ở terminal thứ 2, đã kích hoạt `.venv`):
```powershell
python -m pytest tests/ -v -k "token or tenant or archived or 401 or 404 or health_stays"
```
**Đạt khi:** tất cả `PASSED`.

**4.2 – Test tay trên Swagger** (dùng tiếp ID_HS ở nhiệm vụ 2):

| # | Làm | Đạt khi |
|---|---|---|
| 1 | Bấm **Authorize → Logout**, gọi `GET /api/v1/matters` | Mã **401** (không có token bị từ chối) |
| 2 | **Authorize** bằng `dev-token-bob-0002` (người của tổ chức khác), gọi `GET /api/v1/matters/{matter_id}` với ID_HS | Mã **404** (không thấy hồ sơ của alice) |
| 3 | **Logout**, **Authorize** lại bằng `dev-token-alice-0001`, gọi `DELETE /api/v1/matters/{matter_id}` với ID_HS | Mã 200, `"status": "archived"` |
| 4 | Gọi `POST /api/v1/research` với ID_HS | Mã **409** (hồ sơ đã lưu trữ thì không được ghi) |
| 5 | Gọi `GET /api/v1/matters/{matter_id}/history` với ID_HS | Mã **200** (vẫn được xem) |

---

### ✅ Nhiệm vụ 3: Thống nhất định dạng request/response với frontend

Phần này không có test tự động – phải đối chiếu bằng mắt và **cần nhóm 9 xác nhận**.

| # | Làm | Đạt khi |
|---|---|---|
| 1 | Trang `/docs`, kéo xuống cuối, mục **Schemas** → mở `MatterOut`, `HistoryOut`, `SourceHit`, `ResearchResponse` | Tên trường + kiểu khớp với mục 4 trong `API_CONTRACT.md` |
| 2 | So response thật ở nhiệm vụ 2 với ví dụ JSON ở mục 3 của `API_CONTRACT.md` | Không thiếu / thừa trường |
| 3 | Gửi `API_CONTRACT.md` cho bạn số 9 | Bạn số 9 đồng ý → mới tính là "đã thống nhất" |

---

## BƯỚC 3 – Dọn dẹp

```powershell
docker exec vn_tax_db psql -U vntax_admin -d vntax_copilot -c "DELETE FROM legal_chunks WHERE citation_path LIKE '%DEMO-01'; DELETE FROM legal_documents WHERE doc_code='DEMO-01';"
```
- Tắt server: bấm **Ctrl+C** ở terminal đang chạy uvicorn.
- Tắt DB: `cd ..` rồi `docker compose stop`.

---

## Lỗi hay gặp

| Lỗi | Cách sửa |
|---|---|
| `Fatal error in launcher: Unable to create process ...` | `.venv` tạo ở thư mục cũ rồi bị di chuyển → tạo lại: `deactivate`, `Remove-Item -Recurse -Force .venv`, rồi làm lại bước 1a (từ `python -m venv .venv`). Nếu xóa báo *Access is denied*: tắt hết server/test đang chạy (Ctrl+C) rồi xóa lại |
| `No module named fastapi` / `pytest` | Chưa kích hoạt `.venv` (đầu dòng không có `(.venv)`) → `.venv\Scripts\Activate.ps1` |
| `file or directory not found: tests/` | (1) Đang đứng ở thư mục gốc `VN-tax-copilot` → `cd backend` rồi chạy lại. (2) Đang ở nhánh chưa có code backend → `git switch feature/08-backend-matter-services` (hoặc `develop` sau khi đã merge) |
| Test báo `ERROR` hàng loạt, có dòng `Connection refused ... port 5432` | Container DB tắt hoặc đã bị xóa → `docker compose up -d db` (ở thư mục gốc; dữ liệu vẫn còn trong volume) |
| Mọi API trả **401** | Chưa bấm **Authorize** trên Swagger, hoặc `.env` thiếu dòng `AUTH_TOKENS` (copy lại từ `.env.example`, chạy lại server) |
| `connection refused` khi chạy test | Docker / DB chưa bật → `docker compose up -d db` |
| Bước 2 tìm kiếm trả `[]` | Chưa nạp dữ liệu demo (nhiệm vụ 2, ②), hoặc nạp khi bảng chưa có → chạy server một lần rồi nạp lại |
| `port 8000 already in use` | Có server khác đang chạy (có thể container `vn_tax_backend`): `docker compose stop backend` |

---

## Phụ lục A – Danh sách test

| File | Kiểm tra gì | Số test |
|---|---|---|
| `tests/test_matters.py` | Tạo/xem/sửa/lưu trữ hồ sơ, lọc, phân trang, validate, cô lập tenant, lịch sử | 16 |
| `tests/test_cors.py` | Frontend `localhost:3000` gọi được backend | 5 |
| `tests/test_sources_research.py` | Token (401), quyền (404/409), tìm kiếm, xem nguồn, `/research` | 16 |
| `tests/conftest.py`, `tests/helpers.py` | Thiết lập chung: DB test, token test | – |

Không đặt `TEST_DATABASE_URL` → test chạy trên SQLite (file `test.db`, không cần Docker) – dùng khi chỉ muốn kiểm tra nhanh.

**Sau khi sửa code backend**, luôn chạy lại `python -m pytest` trước khi commit/push – thấy `failed` là có chỗ hỏng.
