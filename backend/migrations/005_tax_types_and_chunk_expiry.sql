-- PostgreSQL only. Chạy SAU 004. Sao lưu DB trước khi chạy. Chạy lại nhiều lần vẫn an toàn.
-- Đồng bộ registry nhóm 5 (SCRUM-40): tax_types (văn bản + đoạn) và ngày hết hiệu lực riêng của đoạn.
BEGIN;

ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS tax_types json NOT NULL DEFAULT '[]';
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS tax_types json NOT NULL DEFAULT '[]';
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS expiry_date timestamp without time zone;

-- Dữ liệu cũ: lấy nhãn sắc thuế đã xác minh trong legal_document_tax_scopes
UPDATE legal_documents d SET tax_types = s.types
FROM (SELECT doc_id, json_agg(tax_type ORDER BY tax_type) AS types
      FROM legal_document_tax_scopes GROUP BY doc_id) s
WHERE s.doc_id = d.id AND d.tax_types::text = '[]';
UPDATE legal_chunks c SET tax_types = d.tax_types
FROM legal_documents d WHERE d.id = c.doc_id AND c.tax_types::text = '[]';

COMMIT;
