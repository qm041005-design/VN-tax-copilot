# 📘 BACKEND GUIDE – VN Tax Copilot

Tài liệu giải thích backend cho **mọi thành viên** (kể cả người chưa từng dùng FastAPI).
Muốn chạy thử → `README.md`. Muốn biết gửi/nhận JSON thế nào → `API_CONTRACT.md`.

Jira: SCRUM-12 (khung backend, hồ sơ), SCRUM-24 (tìm kiếm, nguồn, lịch sử, xác thực) · Công nghệ: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL (pgvector) · Người phụ trách: thành viên 8.

---

## 1. Backend làm gì trong hệ thống?

Backend là **cửa ngõ duy nhất** giữa giao diện web và dữ liệu. Frontend không đọc DB trực tiếp, mà gọi API của backend.

```
 ┌──────────────┐  HTTP + JSON   ┌──────────────────────────┐        ┌───────────────────────┐
 │  Frontend    │ ─────────────▶ │  Backend (FastAPI)       │ ─────▶ │  PostgreSQL            │
 │  (nhóm 9)    │ ◀───────────── │  - kiểm tra token        │ ◀───── │  matters, history,     │
 │  3 cột       │                │  - hồ sơ, lịch sử        │        │  audit_logs            │
 └──────────────┘                │  - tìm & xem nguồn luật  │        │  legal_documents,      │
                                 │  - ghi audit log         │        │  legal_chunks (nhóm 5) │
                                 └───────────┬──────────────┘        └───────────────────────┘
                                             │ (sau này) gọi module AI
                                             ▼
                                 Retrieval (nhóm 6) · Guardrails (nhóm 7) · Prompt/Export (nhóm 1)
```

Các chức năng hiện có:

| Chức năng | Ý nghĩa nghiệp vụ |
|---|---|
| **Hồ sơ vụ việc** (Matter) | Chuyên viên gom các câu hỏi về một khách hàng/vụ việc vào một hồ sơ (cột 1 giao diện) |
| **Tra cứu** (`/research`) | Nhận câu hỏi → tìm đoạn luật liên quan → lưu câu hỏi + trích dẫn vào lịch sử hồ sơ (cột 2) |
| **Nguồn luật** (`/sources`) | Tìm đoạn luật theo từ khóa, xem nguyên văn Điều/Khoản/Điểm (cột 3 – Citation Drawer) |
| **Xác thực** | Mỗi request phải có token; token cho biết người gọi là ai, thuộc tổ chức (tenant) nào |
| **Audit log** | Ghi lại ai làm gì, lúc nào – yêu cầu kiểm toán của RFP |

---

## 2. Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py                    # Điểm khởi động: tạo app, tạo bảng, bật CORS, /health
│   ├── core/                      # Hạ tầng dùng chung
│   │   ├── config.py              #   Đọc cấu hình từ .env / biến môi trường
│   │   ├── database.py            #   Kết nối DB: engine, Session, Base, get_db()
│   │   └── security.py            #   Kiểm tra token "Authorization: Bearer ..." → CurrentUser
│   ├── models/                    # Cấu trúc BẢNG trong DB
│   │   ├── matter.py              #   matters, research_history
│   │   ├── audit.py               #   audit_logs
│   │   ├── legal_source.py        #   legal_documents, legal_chunks (CHỈ ĐỌC, schema của nhóm 5)
│   │   └── base_mixins.py         #   utcnow()
│   ├── schemas/                   # Hình dạng JSON vào/ra + kiểm tra dữ liệu (Pydantic)
│   │   ├── matter.py              #   hồ sơ, lịch sử, Citation
│   │   └── source.py              #   kết quả tìm kiếm, nguyên văn nguồn, research
│   ├── services/                  # Logic nghiệp vụ + truy vấn DB
│   │   ├── matter_service.py      #   tạo/sửa/lưu trữ hồ sơ, lưu lịch sử, ghi audit
│   │   └── source_service.py      #   tìm đoạn luật, lấy nguyên văn
│   └── api/v1/                    # Endpoint HTTP (tiền tố /api/v1)
│       ├── __init__.py            #   gom các router
│       ├── matters.py             #   /matters ...
│       ├── sources.py             #   /sources ...
│       └── research.py            #   /research
├── requirements.txt               # Thư viện Python
├── Dockerfile, .dockerignore      # Đóng gói container
├── .env.example                   # Mẫu cấu hình (copy thành .env)
├── README.md                      # Cách chạy
├── BACKEND_GUIDE.md               # File này
└── API_CONTRACT.md                # Hợp đồng dữ liệu với frontend
```

---

## 3. Kiến trúc 3 tầng (quan trọng nhất)

```
Request ─▶ api/v1/*.py        nhận HTTP, kiểm tra quyền, gọi service, trả JSON   (không viết SQL ở đây)
              │ dùng schemas/ để kiểm tra dữ liệu vào/ra (sai → 422 tự động)
              ▼
           services/*.py      logic nghiệp vụ, truy vấn DB, ghi audit
              │ dùng models/
              ▼
           PostgreSQL         qua core/database.py
```

Vì sao tách tầng: mỗi file một việc → sửa chỗ này không vỡ chỗ khác; module nhóm khác (vd xuất DOCX) gọi thẳng service mà không cần đi qua HTTP.

---

## 4. Một request đi qua những đâu? (ví dụ `POST /api/v1/research`)

1. Frontend gửi câu hỏi kèm header `Authorization: Bearer dev-token-alice-0001`.
2. `core/security.py` kiểm tra token → biết người gọi là `alice`, tenant `thtax`. Sai/thiếu token → **401**.
3. `schemas/source.py::ResearchRequest` kiểm tra body (câu hỏi rỗng, ngày sai định dạng…) → sai thì **422**.
4. `api/v1/research.py` lấy hồ sơ theo `matter_id`, **chỉ trong tenant của alice** → không có thì **404**; hồ sơ đã lưu trữ → **409**.
5. `services/source_service.py::search` tìm các đoạn luật khớp câu hỏi (lọc theo ngày hiệu lực nếu có).
6. `services/matter_service.py::add_history` lưu câu hỏi + danh sách trích dẫn vào `research_history`, ghi 1 dòng `audit_logs` – cả hai trong **cùng một giao dịch**.
7. Trả **201** gồm bản ghi lịch sử + danh sách nguồn tìm được.

---

## 5. Cơ sở dữ liệu

| Bảng | Ai ghi | Nội dung |
|---|---|---|
| `matters` | Backend | Hồ sơ: `id` (UUID), `tenant_id`, `title`, `client_name`, `description`, `tax_types` (`["VAT","CIT","PIT"]`), `tax_period`, `status` (`active`/`archived`), `created_by`, `created_at`, `updated_at` |
| `research_history` | Backend | Mỗi lượt tra cứu: `matter_id`, `actor`, `question`, `tax_type`, `tax_period`, `research_as_of`, `material_facts`, `answer`, `citations` (JSON), `warnings` (JSON), `review_status` (`draft`…), `answer_version`, `created_at` |
| `audit_logs` | Backend | Nhật ký chỉ thêm, không sửa/xóa: `actor`, `action` (vd `matter.create`), `resource_type`, `resource_id`, `detail`, `created_at` |
| `legal_documents` | Nhóm 5 (Data) | Văn bản luật: `doc_code` (vd `48/2024/QH15`), `title`, `doc_type` (`LUAT`/`NGHI_DINH`/`THONG_TU`/`CONG_VAN`), `hierarchy_level` (1–4), `effective_date`, `expiry_date`, `source_url`… |
| `legal_chunks` | Nhóm 5 (Data) | Đoạn luật đã tách theo Điều → Khoản → Điểm: `article_number`, `clause_number`, `point_letter`, `citation_path`, `content`… |

Bảng được tự tạo khi server khởi động (`create_all`). Lưu ý: `create_all` **không sửa** bảng đã có – đổi cột thì phải xóa DB dev (`docker compose down -v`) hoặc dùng Alembic (sprint sau).

---

## 6. Xác thực và quyền truy cập

**Xác thực (bạn là ai?)** – bản tối thiểu cho môi trường thử nghiệm:
- Server đọc danh sách token từ biến `AUTH_TOKENS`, mỗi token gắn sẵn với 1 user và 1 tenant.
- Client gửi `Authorization: Bearer <token>`. Không có / sai → **401**.
- Client **không thể tự khai** tenant: tenant luôn lấy từ token.
- Chưa có: hết hạn token, đăng nhập SSO/MFA, phân vai trò. Sprint sau chỉ cần thay hàm `get_current_user` trong `core/security.py`, các endpoint giữ nguyên.

**Quyền (bạn được làm gì?)**

| Tình huống | Kết quả |
|---|---|
| Xem/sửa hồ sơ của tenant khác | **404** (không trả 403 để người ngoài không biết hồ sơ có tồn tại) |
| Sửa / thêm lịch sử / tra cứu trên hồ sơ đã lưu trữ | **409** – hồ sơ lưu trữ chỉ được xem |
| Xem hồ sơ / lịch sử của hồ sơ đã lưu trữ | Được (giữ dữ liệu cho kiểm toán) |
| Nguồn luật | Dùng chung cho mọi tenant (luật là dữ liệu công khai) nhưng vẫn phải có token |
| `/health` | Không cần token (dùng cho healthcheck) |

---

## 7. Quy tắc thiết kế cần nhớ khi sửa code

- **Mọi truy vấn dữ liệu nghiệp vụ phải lọc `tenant_id`** của người gọi.
- **Không tin client**: `tenant_id`, `created_by`, `actor` luôn lấy từ token, không lấy từ body.
- **Xóa mềm**: `DELETE` chỉ đổi `status = archived`.
- **Audit cùng giao dịch** với thao tác chính (cùng thành công hoặc cùng hủy).
- **Thời gian lưu UTC**; frontend đổi sang giờ Việt Nam khi hiển thị.
- **Độ dài trong schema = độ dài cột DB**, và cột NOT NULL phải chặn `null` ngay ở schema → lỗi trả **422** thay vì **500**.
- **Danh sách hồ sơ mặc định ẩn hồ sơ đã lưu trữ** (`status=all` để xem tất cả).

---

## 8. Các nhóm khác nối vào backend thế nào?

| Nhóm | Nối ở đâu | Ghi chú |
|---|---|---|
| **9 – Frontend** | Gọi các API trong `API_CONTRACT.md` | Gửi header `Authorization`; CORS đã mở cho `localhost:3000` |
| **5 – Data (Parser & DB)** | Nạp dữ liệu vào `legal_documents`, `legal_chunks` | `app/models/legal_source.py` phải khớp cột với `data_pipeline/registry/models.py`. Đổi cột → báo backend |
| **6 – Retrieval** | Thay nội dung hàm `source_service.search` bằng Hybrid Search (BM25 + vector) | Giữ nguyên đầu vào/đầu ra `[(chunk, score)]` thì API không phải đổi |
| **7 – Guardrails** / **1 – Prompt** | Sinh `answer` trong `api/v1/research.py` (chỗ có ghi chú `shortcut:`) | Che thông tin cá nhân trước khi gửi câu hỏi ra dịch vụ AI bên ngoài |
| **1 – Export DOCX** | Gọi `matter_service.get_matter` / `list_history` để lấy dữ liệu xuất báo cáo | Thêm endpoint export theo mục 9 |
| **3 – DevOps** | `backend/Dockerfile`, service `backend` trong `docker-compose.yml`, healthcheck `GET /health` | Biến môi trường cần đặt: `DATABASE_URL`, `AUTH_TOKENS`, `CORS_ORIGINS` |

Hiện trạng tìm kiếm: so khớp từ khóa (ILIKE) – đủ để nối luồng, **chưa đủ chất lượng** cho sản phẩm. `answer` hiện luôn `null`.

---

## 9. Thêm tính năng mới

**Thêm endpoint** (ví dụ `/api/v1/exports`):
1. `schemas/export.py` – khai báo body/response.
2. `services/export_service.py` – viết logic (nhớ lọc `tenant_id`).
3. `api/v1/export.py` – tạo `APIRouter`, viết route gọi service.
4. `api/v1/__init__.py` – thêm `api_router.include_router(export.router)`.
5. Cập nhật `API_CONTRACT.md` và báo frontend.

**Thêm bảng**: tạo model trong `app/models/` và **import vào `app/models/__init__.py`** (không import thì bảng không được tạo).

---

## 10. Hỏi đáp nhanh

- **Mọi API trả 401?** Thiếu header `Authorization` hoặc `.env` thiếu `AUTH_TOKENS`.
- **`Fatal error in launcher`?** Thư mục `.venv` bị di chuyển sau khi tạo → tạo lại `.venv` (README mục 5). `.venv` mỗi người tự tạo, không có trên GitHub.
- **`/docs` lỗi kết nối DB?** Chưa `docker compose up -d db`; kiểm tra `/health`.
- **Đổi cột mà DB không đổi?** `create_all` không migrate – xem mục 5.
- **Frontend báo CORS error?** Thêm địa chỉ frontend vào `CORS_ORIGINS`.
- **Test ở đâu?** Trên nhánh `feature/08-backend-matter-services`: `backend/tests/` và hướng dẫn `backend/TESTING.md`.

## 11. Việc tiếp theo (Sprint 3+)

Đăng nhập SSO/JWT + phân quyền (researcher / reviewer / admin / auditor) · Alembic migration · Hybrid Retrieval (nhóm 6) · sinh câu trả lời AI + guardrails (nhóm 7, 1) · luồng duyệt draft → approved · xuất DOCX/PDF.
