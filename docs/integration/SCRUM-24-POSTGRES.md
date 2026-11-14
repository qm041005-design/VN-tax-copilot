# SCRUM-24 — kiểm thử PostgreSQL, Docker và nguồn công khai

Ngày thực hiện: 14/11/2026. Tác giả phần tích hợp: Đặng Minh Quân.

## Phạm vi đã kiểm tra

- 168 test đạt trên PostgreSQL 16 thật trong database `vntax_test` biệt lập: backend, importer, guardrails, BM25 và parser. Có một cảnh báo deprecation từ thư viện TestClient, không có test fail.
- Docker Compose project `scrum24review`: db, backend, frontend đều healthy. Lint và production build frontend chạy thành công trong image Linux.
- Parser của Duyên đọc trích đoạn nguyên văn Điều 1–3 từ PDF Luật 48/2024/QH15, trang PDF 1 (trang in 77), lưu 3 đoạn vào PostgreSQL qua importer. Tìm kiếm/API trả lại đúng nguồn, trang, nội dung; mở lịch sử sau restart backend thành công.
- Không có token → 401; CORS preflight từ origin frontend → 200; frontend HTTP → 200.
- Guardrails trả abstain vì chưa có assessor chuyên môn; không bật sufficient giả cho văn bản thật.
- Migration chạy trên database riêng `vntax_migration_test`, giữ Khoản cũ `1`, đổi kiểu sang varchar và nhận `1a`; áp dụng lại migration thành công.

Bằng chứng máy đọc được: [smoke JSON](../../backend/evidence/scrum24-public-source-smoke.json).
Trích đoạn có hash PDF và nguồn: [public_law_excerpt.json](../../backend/tests/fixtures/public_law_excerpt.json).

## Những thay đổi để ghép Docker của Phúc

1. Giữ context backend ở gốc repo, copy ai_engine và data_pipeline/parser vào image.
2. Giữ AUTH_TOKENS/CORS khi ghép Compose. POSTGRES_* và DATABASE_URL khớp nhau.
3. Truyền NEXT_PUBLIC_API_BASE_URL và NEXT_PUBLIC_DEV_API_TOKEN lúc build Next.js; thay các giá trị này phải build lại frontend. Token này công khai trong browser, chỉ dành demo local. Không dùng làm cơ chế đăng nhập doanh nghiệp.
4. Bỏ container_name cố định để các project Compose không đụng nhau; bind cổng vào 127.0.0.1. Cho phép đổi DB_PORT/BACKEND_PORT/FRONTEND_PORT trong .env.
5. Thêm frontend/.dockerignore; chạy lint trước build ngay trong Dockerfile.
6. CI dùng PostgreSQL service, chạy toàn bộ pytest và smoke parser → DB → HTTP API, bên cạnh job lint/build frontend.

## Chạy lại

Sao chép `.env.example` thành `.env`, chỉ cấu hình môi trường demo. Chọn project name và cổng riêng nếu máy đã chạy dịch vụ khác. Bản kiểm tra này dùng DB_PORT=15432, BACKEND_PORT=18000, FRONTEND_PORT=13000; API URL và CORS tương ứng. `.env` không được commit.

```powershell
docker compose -p scrum24review up -d --build
docker compose -p scrum24review ps
docker compose -p scrum24review exec -T -e SMOKE_API_TOKEN=dev-token-alice-0001 backend python scripts/smoke_public_source.py --confirm-test-database vntax_copilot
```

Chỉ chạy smoke trên DB demo biệt lập: lệnh tạo hồ sơ giả và thêm đoạn luật. Nếu mã văn bản đã có nội dung khác, script dừng thay vì ghi đè. Đối với test pytest, dùng DB khác như vntax_test vì fixture drop/create bảng. Không đặt TEST_DATABASE_URL trỏ DB demo đang lưu hồ sơ hoặc DB thật.

Khi không cần demo: `docker compose -p scrum24review stop` giữ nguyên volume. Không dùng lệnh xóa volume nếu còn muốn giữ dữ liệu kiểm tra.

## Giới hạn còn lại trước nghiệm thu

Đây là smoke test 1 trang PDF với 3 Điều hoàn chỉnh, không phải kiểm thử đủ 10 văn bản hay 10.000 tài liệu. Ngày hiệu lực trong fixture để null vì chưa qua chuyên gia kiểm tra; kết quả tìm được không chứng minh khả năng áp dụng. Chưa có đánh giá độ chính xác pháp lý, tải, chuyên gia duyệt hoặc LLM thật. Đã kiểm tra HTTP/API và build, chưa kiểm tra thao tác UI đầy đủ bằng trình duyệt. Chưa tự merge develop/main hoặc đóng task Jira.

Các nhánh thành viên được ghép vào nhánh tích hợp để kiểm thử, không ghi đè nhánh cá nhân. PR này có phần việc liên quan backend #2, Docker/CI #8 và parser/guardrails/search; review theo từng module trước khi merge, tránh merge mù các PR trùng phần thay đổi.
