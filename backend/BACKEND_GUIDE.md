# 📘 BACKEND GUIDE – VN Tax Copilot (dành cho thành viên nhóm đọc lại)

Nhánh: `feature/08-backend-matter-services` · Jira: SCRUM-12 · Công nghệ: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL

## 1. Backend làm gì trong cả hệ thống?
Backend là "cửa ngõ dữ liệu" giữa Frontend (React) và database. Ở Sprint 1-2 nó:
1. Quản lý **hồ sơ vụ việc** (Matter) – nơi chuyên viên gom các câu hỏi tra cứu của một khách hàng.
2. Lưu **lịch sử tra cứu** (câu hỏi, câu trả lời, trích dẫn Điều/Khoản/Điểm) vào từng hồ sơ.
3. Ghi **audit log** (ai làm gì, lúc nào) và **cô lập dữ liệu theo tenant**.
4. Tự sinh **Swagger** (`/docs`) để Frontend/AI/QA xem và thử API ngay trên trình duyệt.

Chưa làm (sprint sau): đăng nhập SSO/JWT + phân quyền, API `/research` (nối với AI), xuất DOCX/PDF, duyệt bài.

## 2. Cấu trúc thư mục
```
backend/
├── app/
│   ├── main.py                  # Điểm khởi động: tạo app, tạo bảng, gắn router, /health
│   ├── core/                    # "Hạ tầng" dùng chung
│   │   ├── config.py            #   Cấu hình (đọc .env / biến môi trường)
│   │   ├── database.py          #   Engine, Session, Base, get_db()
│   │   └── security.py          #   Xác định người gọi (tạm: header X-User-Id / X-Tenant-Id)
│   ├── models/                  # Cấu trúc BẢNG trong DB (SQLAlchemy)
│   │   ├── matter.py            #   matters + research_history
│   │   ├── audit.py             #   audit_logs
│   │   └── base_mixins.py       #   utcnow()
│   ├── schemas/                 # Hình dạng JSON vào/ra của API (Pydantic) + validate
│   │   └── matter.py
│   ├── services/                # Logic nghiệp vụ + truy vấn DB
│   │   └── matter_service.py
│   └── api/v1/                  # Endpoint HTTP
│       ├── __init__.py          #   gom router, tiền tố /api/v1
│       └── matters.py           #   các route /matters...
├── tests/                       # Test tự động (pytest, dùng SQLite)
├── requirements.txt             # Thư viện Python
├── Dockerfile                   # Đóng gói container
├── .env.example                 # Mẫu cấu hình
└── README.md                    # Hướng dẫn chạy nhanh
```

## 3. Kiến trúc phân tầng (quan trọng nhất)
```
Client (Frontend/Swagger)
   │  HTTP + JSON
   ▼
api/v1/matters.py   ← nhận request, gọi service, trả response   (KHÔNG chứa logic DB)
   │  dùng schemas/ để kiểm tra dữ liệu vào/ra
   ▼
services/matter_service.py  ← logic nghiệp vụ, truy vấn DB, ghi audit
   │  dùng models/
   ▼
PostgreSQL (qua core/database.py)
```
Vì sao tách tầng? Mỗi file một nhiệm vụ → sửa một chỗ không vỡ chỗ khác, dễ viết test, và module của nhóm khác (vd xuất DOCX) có thể gọi trực tiếp service mà không cần đi qua HTTP.

## 4. Đường đi của một request (ví dụ: tạo hồ sơ)
1. Client gửi `POST /api/v1/matters` với JSON body.
2. FastAPI khớp route trong `api/v1/matters.py::create_matter`.
3. Body được kiểm tra bởi `MatterCreate` (schemas). Sai → trả **422** ngay, code không chạy tiếp.
4. FastAPI tiêm `db` (từ `get_db`) và `user` (từ `get_current_user`).
5. Endpoint gọi `matter_service.create_matter(...)`: tạo object `Matter` (gán `tenant_id`, `created_by` từ `user`), ghi 1 dòng `audit_logs`, `commit`.
6. Kết quả được chuyển sang `MatterOut` và trả **201** + JSON.

## 5. Cơ sở dữ liệu (3 bảng)
**matters** – hồ sơ vụ việc
| Cột | Ý nghĩa |
|---|---|
| id (UUID) | Khóa chính, không đoán được |
| tenant_id | Tổ chức sở hữu – mọi truy vấn đều lọc theo cột này |
| title, client_name, description | Tên hồ sơ, khách hàng, ghi chú |
| tax_types (JSON) | `["VAT","CIT","PIT"]` |
| tax_period | Kỳ tính thuế mặc định, vd `2026` |
| status | `active` / `archived` |
| created_by, created_at, updated_at | Người tạo, thời gian (UTC) |

**research_history** – mỗi lượt tra cứu (bám DAT 03 của RFP)
`id, matter_id (FK→matters), tenant_id, actor, question, tax_type, tax_period, research_as_of, material_facts, answer, citations (JSON), warnings (JSON), review_status (draft…), answer_version, created_at`

**audit_logs** – nhật ký kiểm toán (chỉ thêm, không sửa/xóa)
`id, tenant_id, actor, action (vd matter.create), resource_type, resource_id, detail (JSON), created_at`

## 6. Danh sách API
| Method | Đường dẫn | Mô tả | Mã trả về |
|---|---|---|---|
| GET | /health | Kiểm tra server + DB | 200 |
| POST | /api/v1/matters | Tạo hồ sơ | 201 / 422 |
| GET | /api/v1/matters?status=&q=&limit=&offset= | Danh sách, lọc, phân trang | 200 |
| GET | /api/v1/matters/{id} | Chi tiết | 200 / 404 |
| PATCH | /api/v1/matters/{id} | Sửa một phần | 200 / 404 |
| DELETE | /api/v1/matters/{id} | Archive (xóa mềm) | 200 / 404 |
| POST | /api/v1/matters/{id}/history | Lưu lượt tra cứu | 201 / 404 / 422 |
| GET | /api/v1/matters/{id}/history | Xem lịch sử (header `X-Total-Count`) | 200 / 404 |

Header tạm thời (sẽ thay bằng JWT): `X-User-Id`, `X-Tenant-Id`.

Ví dụ gọi bằng curl:
```bash
curl -X POST http://localhost:8000/api/v1/matters -H "Content-Type: application/json" \
  -d '{"title":"Khấu trừ VAT Q1/2026","client_name":"Công ty ABC","tax_types":["VAT"],"tax_period":"2026"}'
```

## 7. Các quy tắc thiết kế cần nhớ
- **Cô lập tenant:** mọi truy vấn có `tenant_id == user.tenant_id`. Hồ sơ của tenant khác trả **404** (không phải 403) để không lộ việc nó tồn tại.
- **Xóa mềm:** DELETE chỉ đổi `status=archived`; dữ liệu được giữ cho kiểm toán.
- **Audit cùng giao dịch:** dòng audit và thao tác chính được commit cùng lúc.
- **Thời gian UTC** trong DB; frontend đổi sang giờ Việt Nam khi hiển thị.
- **Không tin client** với `tenant_id`/`created_by`: luôn lấy từ `get_current_user`.

## 8. Hướng dẫn mở rộng
**Thêm endpoint mới (vd /api/v1/exports):**
1. `schemas/export.py` – khai báo body/response.
2. `services/export_service.py` – viết logic (nhớ lọc `tenant_id`).
3. `api/v1/export.py` – tạo `APIRouter`, viết route gọi service.
4. Trong `api/v1/__init__.py` thêm `api_router.include_router(export.router)`.
5. Viết test trong `tests/` rồi chạy `python -m pytest -q`.

**Thêm bảng mới:** tạo model trong `app/models/`, **import vào `app/models/__init__.py`**. Lưu ý `create_all` không sửa bảng đã có; muốn thêm/đổi cột phải xóa volume DB dev (`docker compose down -v`) hoặc dùng Alembic.

## 9. Hỏi đáp nhanh
- **`/docs` trống / lỗi kết nối DB?** Chưa bật Postgres: `docker compose up -d db`, kiểm tra `/health`.
- **Đổi cột mà DB không đổi?** Xem mục 8 (create_all không migrate).
- **Test báo lỗi import?** Chạy từ thư mục `backend/` và đã `pip install -r requirements.txt`.
- **Gọi API từ frontend bị CORS?** Chưa bật CORS; thêm `CORSMiddleware` trong `main.py` cho origin `http://localhost:3000` (việc phối hợp với nhóm 9).

## 10. Việc tiếp theo (Sprint 3+)
Đăng nhập SSO/JWT + RBAC (researcher/reviewer/admin/auditor) · Alembic migration · `/api/v1/research` nối AI · luồng duyệt draft→approved · xuất DOCX/PDF · CORS.
