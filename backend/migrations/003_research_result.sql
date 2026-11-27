-- PostgreSQL only. Chạy SAU 002_legal_status_and_registry_columns.sql. Chạy lại nhiều lần vẫn an toàn.
-- Lưu kết quả 6 phần của guardrails cho mỗi lượt tra cứu (mở lại hồ sơ, xuất Word). Không xóa dữ liệu:
-- lượt tra cứu cũ có research_result = NULL.
BEGIN;
ALTER TABLE research_history ADD COLUMN IF NOT EXISTS research_result json;
COMMIT;
