-- PostgreSQL only. Chạy SAU 001_clause_number_text.sql. Sao lưu DB và dừng ghi dữ liệu trước khi chạy.
-- Nâng cấp bảng luật cũ theo schema registry văn bản (data_pipeline/registry, SCRUM-21):
-- thêm cột trạng thái hiệu lực (status) và các cột metadata mới, KHÔNG xóa dữ liệu.
-- Chạy lại nhiều lần vẫn an toàn (IF NOT EXISTS).
BEGIN;

-- legal_documents
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS total_pages integer;
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS status varchar(50) NOT NULL DEFAULT 'CHUA_XAC_DINH';
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS replaces_doc_code varchar(100);
ALTER TABLE legal_documents ALTER COLUMN doc_type SET DEFAULT 'UNKNOWN';
ALTER TABLE legal_documents ALTER COLUMN hierarchy_level SET DEFAULT 5;
CREATE INDEX IF NOT EXISTS ix_legal_documents_status ON legal_documents (status);
CREATE INDEX IF NOT EXISTS ix_legal_documents_replaces_doc_code ON legal_documents (replaces_doc_code);

-- legal_chunks
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS article_intro text;
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS clause_intro text;
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS source_url varchar(1000);
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS effective_date timestamp;
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS status varchar(50) NOT NULL DEFAULT 'CHUA_XAC_DINH';
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS version varchar(50) NOT NULL DEFAULT '1.0';
ALTER TABLE legal_chunks ALTER COLUMN point_letter TYPE varchar(10);
ALTER TABLE legal_chunks ALTER COLUMN hierarchy_level SET DEFAULT 5;
UPDATE legal_chunks SET clause_number = '0' WHERE clause_number IS NULL OR clause_number = '';
ALTER TABLE legal_chunks ALTER COLUMN clause_number SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_legal_chunks_clause_number ON legal_chunks (clause_number);

COMMIT;
