> **Cập nhật SCRUM-24 (14/11/2026):** xem [hướng dẫn tích hợp mới](SCRUM_24_FIXES.md) trước các lệnh bên dưới; backend hiện phụ thuộc ai_engine ở gốc repo, dùng migration cho DB cũ và Docker build context ở gốc.

# Backend – VN Tax Copilot (FastAPI + PostgreSQL)

Phần Backend của dự án **Vietnam Tax Research Copilot with Citations** · Jira: SCRUM-12, SCRUM-24 · Người phụ trách: thành viên 8.

| Tài liệu | Đọc khi nào |
|---|---|
| **README.md** (file này) | Muốn **chạy** backend trên máy trong 5 phút |
| [`BACKEND_GUIDE.md`](BACKEND_GUIDE.md) | Muốn **hiểu** backend làm gì, từng thư mục/file, cách nối với module của nhóm mình |
| [`API_CONTRACT.md`](API_CONTRACT.md) | Frontend / AI cần biết **gửi gì – nhận gì** khi gọi API |
| [`TESTING.md`](TESTING.md) | Muốn **kiểm thử** backend (test tự động trong `tests/` + test tay trên Swagger) |

---

## 1. Chạy backend trên máy (Windows)

**Cần cài:** Git · Python 3.12/3.13 (tích *Add Python to PATH*) · Docker Desktop (mở lên, đợi báo **Running**).

Mở PowerShell, đứng ở thư mục gốc repo `VN-tax-copilot`:

```powershell
# 1. Bật PostgreSQL
docker compose up -d db
docker compose ps                         # thấy vn_tax_db ở trạng thái Up

# 2. Cài môi trường Python (chỉ lần đầu)
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1                # đầu dòng lệnh hiện (.venv)
pip install -r requirements.txt
copy .env.example .env                    # đã có sẵn token thử nghiệm

# 3. Chạy server
python -m uvicorn app.main:app --reload
```

Những lần sau chỉ cần: `docker compose up -d db` → `cd backend` → `.venv\Scripts\Activate.ps1` → `python -m uvicorn app.main:app --reload`.

> **Về thư mục `.venv`:** mỗi người tự tạo trên máy mình (lệnh `python -m venv .venv` ở bước 2), nó **không có trên GitHub**.
> `.venv` gắn chặt với đường dẫn lúc tạo: nếu bạn **di chuyển / đổi tên thư mục dự án** thì phải tạo lại (xem mục 5, lỗi `Fatal error in launcher`).
> Luôn gõ `python -m uvicorn`, `python -m pytest` (thay vì `uvicorn`, `pytest` trơn) để giảm lỗi này.

**Cách khác – chạy cả backend bằng Docker** (không cần cài Python):
```powershell
docker compose up -d --build db backend
```
> Không chạy `docker compose up` trơn: `frontend/` chưa có Dockerfile nên sẽ lỗi ở bước build frontend.

**Kiểm tra:**

| Địa chỉ | Phải thấy |
|---|---|
| http://localhost:8000/health | `{"status":"ok","database":true,...}` |
| http://localhost:8000/docs | Trang Swagger để thử API |

Dừng server: `Ctrl+C`. Tắt database: `docker compose stop`.

---

## 2. Thử API trên Swagger

1. Mở http://localhost:8000/docs → bấm **Authorize** → dán `dev-token-alice-0001` (không gõ chữ `Bearer`) → **Authorize** → **Close**.
2. `POST /api/v1/matters` → **Try it out** → dán body → **Execute**:
   ```json
   {"title": "Khấu trừ VAT đầu vào Q1/2026", "client_name": "Công ty TNHH ABC", "tax_types": ["VAT"], "tax_period": "2026"}
   ```
   Kết quả **201** kèm `id`. Copy `id` này.
3. `POST /api/v1/research`:
   ```json
   {"matter_id": "<id vừa copy>", "question": "Thuế suất GTGT phổ thông là bao nhiêu?", "tax_type": "VAT"}
   ```
4. `GET /api/v1/matters/{matter_id}/history` → thấy lượt tra cứu vừa lưu.

Dữ liệu luật (bảng `legal_documents`, `legal_chunks`) do nhóm Data nạp. Khi chưa có, `/research` trả `sources: []` kèm cảnh báo "Không tìm thấy căn cứ" – đó là đúng thiết kế, không phải lỗi.

Token thử nghiệm có sẵn trong `.env.example`:

| Token | User | Tenant (tổ chức) |
|---|---|---|
| `dev-token-alice-0001` | alice | thtax |
| `dev-token-bob-0002` | bob | other |

---

## 3. Cấu hình (`backend/.env`)

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | Có | Chuỗi kết nối Postgres. Mặc định trỏ tới container `vn_tax_db` qua `localhost:5432` |
| `AUTH_TOKENS` | Có | Danh sách `token:user_id:tenant_id`, ngăn cách bằng dấu phẩy, token ≥ 16 ký tự. Rỗng → mọi API trả 401. Sai định dạng → server không khởi động |
| `CORS_ORIGINS` | Không | Địa chỉ frontend được gọi backend (mặc định `http://localhost:3000,http://127.0.0.1:3000`) |
| `APP_ENV` | Không | `dev` / `staging` / `prod` |

Sửa `.env` xong phải tắt và chạy lại `uvicorn`. Khi chạy bằng Docker, các biến lấy từ `docker-compose.yml` (có giá trị mặc định cho dev).

---

## 4. Nối với Frontend (nhóm 9)

- Chạy backend (mục 1) và frontend (`npm run dev`, cổng 3000) cùng lúc. CORS đã cho phép `http://localhost:3000`.
- Mọi request gửi kèm header `Authorization: Bearer dev-token-alice-0001`.
- Định dạng dữ liệu, kiểu TypeScript, mã lỗi: [`API_CONTRACT.md`](API_CONTRACT.md).

---

## 5. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| Mọi API trả **401** | Chưa Authorize trên Swagger / frontend chưa gửi header `Authorization`; hoặc `.env` thiếu `AUTH_TOKENS` (copy lại từ `.env.example`, rồi chạy lại server) |
| `/health` báo `"database": false` | Docker chưa chạy hoặc chưa `docker compose up -d db` |
| `Fatal error in launcher: Unable to create process using ...python.exe` | `.venv` được tạo ở thư mục cũ rồi bị di chuyển. Tạo lại (đứng ở `backend`): `deactivate` → `Remove-Item -Recurse -Force .venv` → `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt`. Nếu báo *Access is denied* khi xóa: tắt mọi terminal đang chạy server/test rồi xóa lại |
| `No module named fastapi` / `uvicorn` | Chưa kích hoạt `.venv` (đầu dòng lệnh không có `(.venv)`) hoặc chưa `pip install -r requirements.txt`. Trong VS Code: **Ctrl+Shift+P → Python: Select Interpreter** → chọn `backend\.venv\Scripts\python.exe` |
| `Activate.ps1 ... running scripts is disabled` | Chạy `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` rồi kích hoạt lại |
| `Could not open requirements file` / `ModuleNotFoundError: app` | Đứng sai thư mục, phải ở `VN-tax-copilot\backend` |
| `port is already allocated` (5432) | Máy đang chạy Postgres khác, tắt nó đi |
| `port 8000 already in use` | Đã có server chạy (có thể là container `vn_tax_backend`): `docker compose stop backend` hoặc dùng `--port 8001` |
| Đổi cột trong model mà DB không đổi | `create_all` không sửa bảng đã có: `docker compose down -v` rồi `docker compose up -d db` (mất dữ liệu dev) |
| Frontend báo **CORS error** | Frontend chạy ở địa chỉ khác `localhost:3000` → thêm địa chỉ đó vào `CORS_ORIGINS` |

Xem dữ liệu trong DB: `docker exec -it vn_tax_db psql -U vntax_admin -d vntax_copilot`, gõ `\dt`, `SELECT title FROM matters;`, `\q` để thoát.

---

## 6. Quy tắc làm việc nhóm

- Không commit thẳng vào `main` / `develop`. Pull Request vào **`develop`** (xem `CONTRIBUTING.md`).
- Commit theo mẫu `<loại>(<mã-jira>): mô tả`, ví dụ `feat(SCRUM-24): them API research`. Mã Jira trong message giúp commit hiện trong mục **Development** của task trên Jira.
- **Không commit** `.venv/`, `.env`, `*.db`, `__pycache__/` (đã có trong `.gitignore`).
