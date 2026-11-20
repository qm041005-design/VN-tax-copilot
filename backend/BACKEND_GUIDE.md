# BACKEND GUIDE – VN Tax Copilot

Giải thích backend cho mọi thành viên, kể cả người chưa dùng FastAPI.
Cài đặt, chạy và kiểm thử → [`HUONG_DAN_TEST.md`](HUONG_DAN_TEST.md) · Gửi/nhận JSON → [`API_CONTRACT.md`](API_CONTRACT.md).

Jira: SCRUM-12 (khung backend, hồ sơ), SCRUM-24 (tìm kiếm, nguồn, lịch sử, xác thực), SCRUM-33 (lưu kết quả 6 phần, xuất Word) · Python 3.12/3.13, FastAPI, SQLAlchemy 2, PostgreSQL · Phụ trách: Luân (thành viên 8).

---

## 1. Backend làm gì?

Backend là cửa duy nhất giữa giao diện và dữ liệu. Frontend không đọc DB, chỉ gọi API.

```
Frontend (Phước) ──HTTP+JSON──▶ Backend (FastAPI) ──▶ PostgreSQL
                                 │  token, quyền hồ sơ, audit log
                                 ├─▶ ai_engine/retrieval   (BM25 – Thanh)
                                 ├─▶ ai_engine/guardrails  (kiểm duyệt kết quả – An)
                                 └─▶ ai_engine/synthesis + export_service (báo cáo Word – Quân)
```

| Chức năng | Ý nghĩa nghiệp vụ |
|---|---|
| Hồ sơ vụ việc | Gom các câu hỏi về một khách hàng/vụ việc (cột trái giao diện) |
| Tra cứu `/research` | Tìm đoạn luật → guardrails ra kết quả 6 phần → **lưu vào lịch sử hồ sơ** (cột giữa) |
| Xuất Word | Tải báo cáo `.docx` của một lượt tra cứu, kiểm tra quyền trước khi xuất |
| Nguồn luật `/sources` | Tìm và xem nguyên văn Điều/Khoản/Điểm (cột phải) |
| Xác thực + audit | Token cho biết người gọi và tổ chức; mọi thao tác ghi vào `audit_logs` |

## 2. Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py                      # Khởi động app, tạo bảng, CORS, /health
│   ├── core/
│   │   ├── config.py                #   Đọc cấu hình .env
│   │   ├── database.py              #   engine, Session, get_db()
│   │   └── security.py              #   Bearer token → CurrentUser(user_id, tenant_id)
│   ├── models/                      # Bảng DB
│   │   ├── matter.py                #   matters, research_history
│   │   ├── audit.py                 #   audit_logs
│   │   └── legal_source.py          #   legal_documents, legal_chunks, legal_document_tax_scopes
│   ├── schemas/                     # JSON vào/ra (Pydantic) – sai dữ liệu → 422
│   │   ├── matter.py                #   hồ sơ, lịch sử, Citation
│   │   ├── source.py                #   tìm kiếm, nguyên văn, research
│   │   └── ingestion.py             #   định dạng file nạp luật
│   ├── services/                    # Logic nghiệp vụ
│   │   ├── matter_service.py        #   hồ sơ, lịch sử, audit
│   │   ├── source_service.py        #   lọc + tìm đoạn luật (BM25)
│   │   ├── guarded_research_service.py  # đổi đoạn luật thành đầu vào guardrails
│   │   ├── legal_ingestion_service.py   # nạp văn bản luật (importer)
│   │   ├── legal_metadata.py        #   kỳ thuế, nhãn Khoản
│   │   └── export_service.py        #   tạo file Word (code của Quân)
│   └── api/v1/                      # Endpoint /api/v1/...
│       ├── matters.py               #   hồ sơ, lịch sử, xuất Word
│       ├── research.py              #   tra cứu
│       └── sources.py               #   nguồn luật
├── migrations/                      # SQL nâng cấp DB cũ (001 → 004)
├── scripts/                         # import_legal_document, export_bm25_retrieval, smoke_public_source
├── tests/                           # pytest
├── evidence/                        # Bằng chứng smoke test trên PostgreSQL (của Quân)
├── SCRUM_24_FIXES.md, PARSER_IMPORT.md  # Ghi chú tích hợp của Quân
└── BACKEND_GUIDE.md, API_CONTRACT.md, HUONG_DAN_TEST.md
```

## 3. Kiến trúc 3 tầng

```
api/v1/*.py     nhận HTTP, kiểm tra quyền, gọi service, trả JSON (không viết SQL)
   ▼ dùng schemas/ kiểm tra dữ liệu
services/*.py   logic nghiệp vụ, truy vấn DB, ghi audit
   ▼ dùng models/
PostgreSQL
```

## 4. Một lượt tra cứu đi qua đâu (`POST /api/v1/research`)

1. `core/security.py` kiểm tra token → biết người gọi và tổ chức. Sai/thiếu → **401**.
2. `schemas/source.py` kiểm tra body. Sai → **422**.
3. `api/v1/research.py` lấy hồ sơ trong tổ chức của người gọi. Không có → **404**; đã lưu trữ → **409**.
4. `source_service.search`: lọc theo sắc thuế (bảng nhãn), kỳ thuế/ngày hiệu lực (cả cấp văn bản và cấp đoạn), loại văn bản → xếp hạng BM25.
5. `guarded_research_service` + `ai_engine/guardrails` ra kết quả `clarify` / `abstain` / `draft` với 6 phần.
6. `matter_service.add_history` lưu câu hỏi (đã che thông tin cá nhân), trích dẫn, cảnh báo và **object 6 phần** vào `research_history`, ghi audit – cùng một giao dịch.
7. Trả **201**.

**Xuất Word** (`GET /matters/{id}/history/{history_id}/export`): kiểm tra token → hồ sơ → lượt tra cứu thuộc hồ sơ → có kết quả 6 phần → nguồn còn trong kho → `prepare_backend_export` đối chiếu với nguyên văn → `export_research_docx` tạo file → ghi audit `history.export_docx`.

## 5. Cơ sở dữ liệu

| Bảng | Ai ghi | Nội dung chính |
|---|---|---|
| `matters` | Backend | `id`, `tenant_id`, `title`, `client_name`, `tax_types`, `tax_period`, `status` (`active`/`archived`) |
| `research_history` | Backend | `question`, `material_facts`, `answer`, `citations`, `warnings`, **`research_result`** (6 phần), `review_status` |
| `audit_logs` | Backend | Chỉ thêm: `actor`, `action` (`matter.create`, `history.create`, `history.export_docx`…), `resource_id` |
| `legal_documents` | Importer (dữ liệu của Duyên) | `doc_code`, `doc_type`, `hierarchy_level`, `effective_date`, `expiry_date`, `version`, `source_url`, `preamble` (căn cứ / mở đầu), 3 trạng thái: `status` (pháp lý), `ocr_quality_status` (`RAW`/`VERIFIED`/`NEEDS_REVIEW`), `expert_review_status` (`PENDING`/`APPROVED`/`REJECTED`) |
| `legal_chunks` | Importer | Điều/Khoản/Điểm, `citation_path`, `content`, `source_page`, `effective_date` riêng của đoạn, `ocr_quality_status`, `expert_review_status` |
| `legal_document_tax_scopes` | Importer | Nhãn sắc thuế của văn bản (`VAT`/`CIT`/`PIT`) |

Bảng tự tạo khi server khởi động (`create_all`), nhưng `create_all` **không sửa** bảng đã có. DB cũ → chạy `migrations/001` → `004` (xem `HUONG_DAN_TEST.md`). Đổi cột trong model thì phải thêm file migration mới và cập nhật `tests/test_migrations.py`.

## 6. Xác thực và quyền

- Token thử nghiệm cấu hình trong `AUTH_TOKENS`, mỗi token gắn 1 user + 1 tổ chức. Client **không** tự khai tổ chức.
- Hồ sơ / lượt tra cứu của tổ chức khác → **404** (không 403, để người ngoài không biết hồ sơ có tồn tại).
- Hồ sơ đã lưu trữ: xem và xuất Word được; sửa, tra cứu, thêm lịch sử → **409**.
- Nguồn luật dùng chung mọi tổ chức nhưng vẫn cần token. `/health` không cần token.
- Chưa có: SSO/MFA, token hết hạn, phân vai trò. Sau này chỉ cần thay `get_current_user`.

**Cấu hình** (`backend/.env`, copy từ `.env.example`; sửa xong phải chạy lại server):

| Biến | Ý nghĩa |
|---|---|
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL |
| `AUTH_TOKENS` | `token:user_id:tenant_id`, ngăn cách bằng dấu phẩy, token ≥ 16 ký tự. Rỗng → mọi API 401; sai định dạng → server không chạy |
| `CORS_ORIGINS` | Địa chỉ frontend được gọi backend (mặc định `localhost:3000`) |
| `APP_ENV` | `dev` / `staging` / `prod` |

## 7. Quy tắc khi sửa code

- Mọi truy vấn dữ liệu nghiệp vụ phải lọc `tenant_id` của người gọi.
- `tenant_id`, `actor`, `created_by` lấy từ token, không lấy từ body.
- `DELETE` hồ sơ chỉ đổi `status = archived`.
- Audit ghi cùng giao dịch với thao tác chính.
- Độ dài/NOT NULL trong schema khớp cột DB, để lỗi là **422** chứ không phải **500**.
- Callback AI (`research_callbacks`) chỉ cấu hình ở server, không nhận từ request.

## 8. Các nhóm nối vào backend

| Nhóm | Nối ở đâu | Trạng thái |
|---|---|---|
| Frontend (Phước) | API trong `API_CONTRACT.md` | Đã nối hồ sơ, tra cứu, lịch sử, nguồn. **Chưa** nối xuất Word (nút hiện tạo `.txt`), chưa gửi `material_facts` |
| Dữ liệu (Duyên) | `scripts/import_legal_document.py` | Nhận đủ metadata parser SCRUM-30: `preamble`, trạng thái OCR, trạng thái duyệt (importer chỉ nhận `PENDING`; phê duyệt do chuyên gia). Model khớp registry, kiểm bằng `tests/test_data_pipeline_sync.py`. Lưu metadata cấp đoạn (intro, ngày hiệu lực, URL) nằm ở nhánh SCRUM-31 của Thanh |
| Retrieval (Thanh) | `ai_engine/retrieval` qua `source_service.search` | BM25 đã dùng |
| Guardrails (An) | `ai_engine/guardrails` qua `guarded_research_service` | Đã nối. Chưa có `assess`/`generate` nên kết quả luôn `clarify`/`abstain`. Metadata cấp đoạn chờ thống nhất |
| Export (Quân) | `export_service.py` + `ai_engine/synthesis/backend_adapter.py` | Đã nối vào API xuất Word |
| DevOps (Phúc) | `backend/Dockerfile`, `docker-compose.yml`, `/health` | Build context ở gốc repo |

## 9. Thêm tính năng mới

1. Schema trong `schemas/`, logic trong `services/` (nhớ lọc `tenant_id`), route trong `api/v1/`.
2. Router mới thì thêm vào `api/v1/__init__.py`. Bảng mới thì import trong `models/__init__.py` và viết migration.
3. Viết test trong `tests/`, cập nhật `API_CONTRACT.md` và báo frontend.
