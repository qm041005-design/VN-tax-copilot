# Backend – VN Tax Copilot (FastAPI + PostgreSQL)

Phần Backend của dự án **Vietnam Tax Research Copilot with Citations**.
Nhánh: `feature/08-backend-matter-services` · Jira: SCRUM-12

Backend làm gì: quản lý **hồ sơ vụ việc** (matter) và lưu **lịch sử tra cứu** (câu hỏi, câu trả lời, trích dẫn Điều/Khoản/Điểm), có cô lập dữ liệu theo tenant và ghi nhật ký kiểm toán. Giải thích chi tiết kiến trúc và từng file: xem [`BACKEND_GUIDE.md`](BACKEND_GUIDE.md).

---

## 1. Chạy backend trên máy bạn (Windows, làm một lần là xong)

### Cần cài sẵn
| Công cụ | Ghi chú |
|---|---|
| Git | https://git-scm.com |
| Python 3.12 hoặc 3.13 | Khi cài tích **Add Python to PATH** |
| Docker Desktop | Để chạy PostgreSQL. Mở Docker Desktop và đợi báo **Running** |

### Các bước
Mở PowerShell và chạy lần lượt:

```powershell
# 1. Lấy code (bỏ qua nếu đã clone)
git clone https://github.com/qm041005-design/VN-tax-copilot.git
cd VN-tax-copilot
git fetch origin
git checkout feature/08-backend-matter-services     # hoặc develop, sau khi đã merge

# 2. Bật database PostgreSQL (từ thư mục gốc repo)
docker compose up -d db
docker compose ps                                   # phải thấy vn_tax_db ở trạng thái running

# 3. Cài môi trường Python
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1                          # đầu dòng lệnh phải hiện (.venv)
pip install -r requirements.txt
copy .env.example .env

# 4. Chạy server
uvicorn app.main:app --reload
```

> **Lưu ý:** chỉ chạy `docker compose up -d db` (hoặc `up -d --build db backend`), **không chạy `docker compose up` trơn** khi `frontend/` chưa có Dockerfile, vì sẽ lỗi ở bước build frontend.

### Kiểm tra đã chạy đúng chưa
| Địa chỉ | Phải thấy |
|---|---|
| http://localhost:8000/health | `{"status":"ok","database":true,...}` |
| http://localhost:8000/docs | Trang Swagger (giao diện thử API) |

Dừng server: bấm `Ctrl+C`. Tắt database: `docker compose stop`.

---

## 2. Thử API ngay trên Swagger (không cần frontend)

1. Mở http://localhost:8000/docs (hiện **chưa cần đăng nhập**, không cần Authorize).
2. (Tùy chọn) Mỗi endpoint có 2 ô header `x-user-id` và `x-tenant-id`; bỏ trống thì mặc định `dev-user` / `thtax`.
3. Bấm `POST /api/v1/matters` → **Try it out** → dán JSON → **Execute**:
```json
{
  "title": "Khấu trừ VAT đầu vào Q1/2026",
  "client_name": "Công ty TNHH ABC",
  "tax_types": ["VAT"],
  "tax_period": "2026"
}
```
4. Kết quả đúng là mã **201** kèm `id`. Copy `id` đó dùng cho các endpoint khác.
5. Lưu một lượt tra cứu: `POST /api/v1/matters/{matter_id}/history`:
```json
{
  "question": "Thuế suất GTGT phổ thông là bao nhiêu?",
  "tax_type": "VAT",
  "answer": "Nội dung trả lời",
  "citations": [{"source_id": "s1", "legal_identifier": "48/2024/QH15", "dieu": "9", "khoan": "1"}]
}
```

Dữ liệu ban đầu là **rỗng**: các hồ sơ bạn thấy là do bạn tự tạo khi thử. Dữ liệu luật thuế là phần của nhóm Data Engineer, không nằm ở backend này.

---

## 3. Danh sách API

Tiền tố: `/api/v1`. **Chưa có đăng nhập** (xem mục *Xác thực tạm thời* bên dưới). Mọi dữ liệu được lọc theo tenant, hồ sơ của tenant khác trả **404**.

| Method | Đường dẫn | Mô tả | Mã trả về |
|---|---|---|---|
| GET | `/health` | Kiểm tra server và DB | 200 |
| POST | `/api/v1/matters` | Tạo hồ sơ | 201, 422 |
| GET | `/api/v1/matters?status=&q=&limit=&offset=` | Danh sách hồ sơ (lọc, phân trang). `status` = `active` (**mặc định**, ẩn hồ sơ đã archive) \| `archived` \| `all` | 200 |
| GET | `/api/v1/matters/{id}` | Chi tiết hồ sơ (xem được cả hồ sơ đã archive) | 200, 404 |
| PATCH | `/api/v1/matters/{id}` | Sửa một phần hồ sơ (`title`, `client_name`, `tax_types` không được `null`) | 200, 404, 422 |
| DELETE | `/api/v1/matters/{id}` | Lưu trữ (archive, xóa mềm) | 200, 404 |
| POST | `/api/v1/matters/{id}/history` | Lưu một lượt tra cứu | 201, 404, 422 |
| GET | `/api/v1/matters/{id}/history?limit=&offset=` | Xem lịch sử tra cứu (tổng số ở header `X-Total-Count`) | 200, 404 |

**Xác thực tạm thời (CHƯA CÓ ĐĂNG NHẬP):** người gọi tự khai 2 header:

| Header | Mặc định | Ý nghĩa |
|---|---|---|
| `X-User-Id` | `dev-user` | Người gọi |
| `X-Tenant-Id` | `thtax` | Tổ chức, dùng để cô lập dữ liệu |

> **Cảnh báo:** vì client tự khai nên ai cũng giả được tenant của người khác, và không đăng nhập vẫn tạo được hồ sơ. Bản này chỉ dùng để **phát triển và thử trong nhóm, KHÔNG triển khai thật**. Việc cô lập dữ liệu theo tenant đã được cài đặt sẵn ở mọi truy vấn; sprint sau chỉ cần thay hàm `get_current_user` trong `app/core/security.py` bằng đăng nhập SSO/JWT thật (kèm phân quyền) mà các endpoint không phải đổi.

**Cấu hình** (`.env` hoặc biến môi trường; xem `.env.example`):

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `CORS_ORIGINS` | Không | Origin frontend được gọi backend, ngăn cách bằng dấu phẩy (mặc định `http://localhost:3000,http://127.0.0.1:3000`) |

Giá trị hợp lệ của `tax_types` / `tax_type`: `VAT` (GTGT), `CIT` (TNDN), `PIT` (TNCN). Giá trị khác bị từ chối (422).

---

## 4. Hướng dẫn riêng cho từng vai trò

### Frontend (nhóm 9)
- Địa chỉ API khi chạy local: `http://localhost:8000`. Xem đủ cấu trúc dữ liệu ở `/docs` hoặc `/openapi.json`.
- Ví dụ gọi bằng `fetch`:
```ts
const res = await fetch("http://localhost:8000/api/v1/matters", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Tenant-Id": "thtax", "X-User-Id": "dev-user" },
  body: JSON.stringify({ title: "Hồ sơ A", client_name: "Công ty ABC", tax_types: ["VAT"] }),
});
const matter = await res.json();
```
- Hiện **chưa có đăng nhập**: gửi `X-User-Id` / `X-Tenant-Id` như ví dụ trên (hoặc bỏ trống để dùng mặc định). Khi backend có đăng nhập thật sẽ báo nhóm để đổi sang `Authorization`.
- Phân trang danh sách: dùng `total`, `limit`, `offset` trong kết quả `GET /matters`. Danh sách **mặc định chỉ có hồ sơ `active`**; muốn hiện cả hồ sơ đã archive thì thêm `?status=all`.
- **CORS đã bật** cho `http://localhost:3000` (đổi bằng `CORS_ORIGINS`). Header `X-Total-Count` của lịch sử tra cứu đã được expose để JS đọc được.

### AI (nhóm 6, 7)
- Sau khi sinh câu trả lời, gọi `POST /api/v1/matters/{id}/history` để lưu. Trường `citations` nhận danh sách đối tượng `{source_id, title, legal_identifier, dieu, khoan, diem, url}`. Cần thêm trường (vd phiên bản, ngày hiệu lực) thì báo backend, sửa ở `app/schemas/matter.py`.
- Backend **chưa có** endpoint `/api/v1/research` gọi AI, sẽ làm ở sprint sau khi các module AI sẵn sàng.

### QA (nhóm 2)
- Chạy test tự động (dùng SQLite, không cần Docker):
```powershell
cd backend
python -m pytest -q          # kết quả đúng: tất cả passed, không có failed/error
```
- Thêm ca test mới vào `backend/tests/` (xem `test_matters.py` làm mẫu, đặc biệt `test_tenant_isolation`). Dùng `auth(user, tenant)` trong `tests/helpers.py` để lấy header định danh tạm. Test CORS ở `test_cors.py`.

### DevOps (nhóm 3)
- `backend/Dockerfile` đã có, `docker-compose.yml` ở gốc repo đã khai báo service `backend` (cổng 8000) trỏ tới service `db`.
- `GET /health` dùng được làm healthcheck.
- Gợi ý: thêm `healthcheck` cho service `db` và chuyển sang Alembic migration (hiện dùng `create_all`).

---

## 5. Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py              # Điểm khởi động, tạo bảng, /health
│   ├── core/                # Cấu hình, kết nối DB, xác định người gọi (security.py, bản tạm)
│   ├── models/              # Cấu trúc bảng DB (matters, research_history, audit_logs)
│   ├── schemas/             # Khuôn JSON vào/ra + kiểm tra dữ liệu
│   ├── services/            # Logic nghiệp vụ, truy vấn DB
│   └── api/v1/              # Các endpoint HTTP
├── tests/                   # Test tự động (pytest)
├── requirements.txt         # Thư viện Python
├── Dockerfile
├── .env.example             # Mẫu cấu hình (copy thành .env)
├── BACKEND_GUIDE.md         # Giải thích chi tiết từng file
└── README.md                # File này
```

---

## 6. Xem dữ liệu trong database

```powershell
docker exec -it vn_tax_db psql -U vntax_admin -d vntax_copilot
```
Trong đó gõ:
```sql
\dt                                    -- liệt kê bảng
SELECT title, client_name FROM matters;
SELECT action, resource_type FROM audit_logs;
\q                                     -- thoát
```
Hoặc dùng DBeaver: host `localhost`, port `5432`, database `vntax_copilot`, user `vntax_admin`, password `vntax_secret`.

Xóa sạch dữ liệu dev (khi đổi cấu trúc bảng): `docker compose down -v` rồi `docker compose up -d db`.

---

## 7. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `Activate.ps1 ... running scripts is disabled` | Chạy `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` rồi kích hoạt lại. |
| `Could not open requirements file` | Đang đứng sai thư mục. Phải ở `...\VN-tax-copilot\backend`. |
| `/health` báo `"database": false` | Chưa bật Docker hoặc `.env` sai. Chạy `docker compose ps` và kiểm tra `DATABASE_URL`. |
| `port is already allocated` (5432) | Máy đang chạy PostgreSQL khác. Tắt nó hoặc đổi cổng trong `docker-compose.yml`. |
| `port 8000 already in use` | Đang có server khác chạy. Tắt terminal cũ hoặc dùng `--port 8001`. |
| Đổi cột trong model mà DB không đổi | `create_all` không sửa bảng đã có. Chạy `docker compose down -v` rồi bật lại DB (dev). |
| `ModuleNotFoundError: app` | Chạy lệnh từ thư mục `backend/`, và đã `pip install -r requirements.txt`. |
| Không dùng được Docker | Tạm đặt trong `.env`: `DATABASE_URL=sqlite:///./dev.db` (chỉ để thử, không dùng khi nộp). |

---

## 8. Quy tắc làm việc nhóm

- Không commit vào `main` hoặc `develop`; làm trên nhánh `feature/...` của mình (xem `CONTRIBUTING.md`).
- Message commit bắt đầu bằng mã Jira, ví dụ: `SCRUM-12 feat(backend): ...`.
- **Không commit** `.venv/`, `.env`, `*.db`, `__pycache__/` (đã có trong `.gitignore`).

## 9. Chưa làm (kế hoạch sprint sau)

**Đăng nhập thật (SSO/JWT)** thay cho header tạm, và phân quyền (researcher, reviewer, admin, auditor), Alembic migration, `/api/v1/research` nối AI, luồng duyệt draft → approved, xuất DOCX/PDF.
