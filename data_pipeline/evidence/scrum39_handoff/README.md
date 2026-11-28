# SCRUM-39 OCR handoff

This directory contains 44 representative OCR pages across 10 legal documents.
Each document JSON uses the ingestion structure:

```json
{
  "metadata": {},
  "ocr_pages": [
    {
      "page": 1,
      "text": "..."
    }
  ]
}
```

This is not full-document OCR. `effective_date` and `expiry_date` remain `null`
when not available in the intake metadata. Team review of tables and values is
still required before production ingestion.
