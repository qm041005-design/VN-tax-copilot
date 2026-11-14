-- PostgreSQL only. Back up the DB and stop writers before applying.
-- Transactional and repeatable; do not drop tables to migrate existing data.
BEGIN;
ALTER TABLE legal_chunks ALTER COLUMN clause_number DROP DEFAULT;
ALTER TABLE legal_chunks ALTER COLUMN clause_number TYPE varchar(20)
    USING clause_number::varchar(20);
ALTER TABLE legal_chunks ALTER COLUMN clause_number SET DEFAULT '0';
CREATE TABLE IF NOT EXISTS legal_document_tax_scopes (
    doc_id integer NOT NULL REFERENCES legal_documents(id),
    tax_type varchar(20) NOT NULL,
    PRIMARY KEY (doc_id, tax_type)
);
COMMIT;
