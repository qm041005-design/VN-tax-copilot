-- PostgreSQL only. Chạy SAU 003. Sao lưu DB trước khi chạy. Chạy lại nhiều lần vẫn an toàn (IF NOT EXISTS).
-- Đồng bộ registry nhóm 5 (SCRUM-30): tách 3 nhóm trạng thái và lưu đoạn mở đầu văn bản.
--   status               : trạng thái pháp lý (đã có)
--   ocr_quality_status   : RAW | VERIFIED | NEEDS_REVIEW
--   expert_review_status : PENDING | APPROVED | REJECTED
BEGIN;

ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS preamble text;
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS ocr_quality_status varchar(50) NOT NULL DEFAULT 'RAW';
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS expert_review_status varchar(50) NOT NULL DEFAULT 'PENDING';
CREATE INDEX IF NOT EXISTS ix_legal_documents_ocr_quality_status ON legal_documents (ocr_quality_status);
CREATE INDEX IF NOT EXISTS ix_legal_documents_expert_review_status ON legal_documents (expert_review_status);

ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS ocr_quality_status varchar(50) NOT NULL DEFAULT 'RAW';
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS expert_review_status varchar(50) NOT NULL DEFAULT 'PENDING';

COMMIT;
