# SCRUM-24 — nhận dữ liệu parser trước khi lưu

`app.services.legal_ingestion_service.ingest_legal_document(db, payload)` là hàm nội bộ, không phải endpoint công khai. Chỉ gọi từ quy trình nhập nguồn công khai đã kiểm tra quyền sử dụng. Caller quản lý transaction và commit/rollback; không cấp khả năng ghi nguồn cho người dùng tra cứu.

## Cách gọi

```python
from app.core.database import SessionLocal
from app.services.legal_ingestion_service import ingest_legal_document

# document_metadata: doc_code, title, doc_type, hierarchy_level,
# issue_date/effective_date/expiry_date, source_url, version, issuer nếu có.
# total_pages, amends_doc_code và replaces_doc_code nếu registry có dữ liệu.
# parsed_chunks: danh sách dictionary trả từ parser, chưa biến đổi ngày lỗi thành null.
payload = {
    "document": document_metadata,
    "chunks": parsed_chunks,
    "tax_types": ["VAT"],  # nhãn do người nhập xác minh, không tự suy ra
    "as_of": "2026-11-14",  # ngày đối chiếu trạng thái, không tự lấy đồng hồ máy
}
with SessionLocal.begin() as db:
    receipt = ingest_legal_document(db, payload)
# Commit chỉ xảy ra khi thoát block thành công. Exception => rollback.
```

Payload được kiểm tra toàn bộ trước khi thêm bản ghi. Lỗi validation phải được trả cho người nhập để sửa, không bắt lỗi rồi tiếp tục ghi các đoạn còn lại. Với lỗi SQL, caller rollback transaction trước khi dùng lại session.

SCRUM-22 cung cấp hai lệnh dùng cùng database và cùng dịch vụ tìm kiếm của backend. Chạy trong container backend sau khi nạp JSON vào container, hoặc từ gốc repo với `PYTHONPATH=.;backend` trên Windows và `DATABASE_URL` trỏ tới DB của backend.

```powershell
python -m backend.scripts.import_legal_document --input /tmp/parser-output.json
python -m backend.scripts.export_bm25_retrieval --benchmark /tmp/benchmark.json --output /tmp/bm25-retrieval.json
```

Lệnh `import_legal_document` nạp một tệp JSON của parser vào registry. Lệnh `export_bm25_retrieval` chạy các câu trong benchmark qua dịch vụ tìm kiếm và ghi ID đoạn theo thứ tự trả về.

`parser-output.json` chứa `document`, `chunks`, `tax_types` và `as_of`. `chunks` là đầu ra `chunk_legal_document` từ các đoạn hoặc trang đã đối chiếu. Giữ toàn văn và số trang PDF đếm từ 1. Đoạn trải nhiều trang cần được parser ghép trước khi nhập. Lệnh nhập in `document_id` và `chunk_ids`.

API mặc định trả 10 đoạn kèm nguồn, Điều/Khoản/Điểm, `source_page`, `version` và các mốc hiệu lực. Script Recall@10 ghi mảng `{case_id, retrieved_passage_ids}` bằng chính `source_id` của API, với cùng nhãn sắc thuế và bộ lọc kỳ/ngày. Nhóm QA dùng tệp này qua tham số `--retrieval` của `evaluation/metrics/recall_at_10.py`. Nhãn `acceptable_passage_ids` phải trỏ tới các ID trong cùng snapshot DB.

Các nhóm `VAT/CIT/PIT` dùng nhãn đã được gán trong registry. `TAX_ADMIN/E_INVOICE` tìm theo nội dung vì enum API hiện chỉ có VAT/CIT/PIT. Script xuất giữ một snapshot nhất quán trong PostgreSQL bằng transaction chỉ đọc với mức cô lập REPEATABLE READ.

## Quy ước

- Ngày hợp lệ: chuỗi YYYY-MM-DD, Python date hoặc datetime không timezone tại 00:00:00 (tương thích parser). Giá trị thiếu là null hoặc không gửi trường.
- Chuỗi rỗng, `invalid`, ngày không tồn tại, timestamp dạng số, chuỗi datetime có timezone hoặc datetime có giờ đều bị từ chối. Không tự bỏ giờ/múi giờ hoặc chuyển dữ liệu lỗi thành null.
- Khoảng hiệu lực là `[effective_date, expiry_date)`. Ngày kết thúc phải sau ngày bắt đầu; bằng nhau là khoảng rỗng, bị chặn. Đúng ngày hết hiệu lực trở đi trả HET_HIEU_LUC. Văn bản hết hiệu lực vẫn được lưu để nghiên cứu lịch sử.
- Ngày thiếu không bị suy đoán. `temporal_status` trong receipt chỉ suy ra từ ngày, chưa chứng minh văn bản còn hiệu lực pháp lý hoặc áp dụng được cho một vụ việc. Không lưu status do parser tự đưa vào như quyết định đã duyệt.
- Giữ Điều/Khoản `1a`. Số 0, chuỗi "0", rỗng/null của Khoản được chuẩn hóa; DB dùng sentinel "0" để tương thích registry, API trả null.
- Ngày ban hành, ngày hết hiệu lực, phiên bản, loại, thứ bậc và mã quan hệ do parser lặp lại ở đoạn phải khớp metadata văn bản. Ngày bắt đầu hiệu lực và URL riêng của đoạn được lưu và ưu tiên khi truy hồi. Registry lưu toàn văn, phần mở đầu Điều/Khoản, số trang PDF và số trang toàn văn bản nếu có.
- Mã văn bản đã tồn tại bị từ chối; không thay nội dung đằng sau một ID đã được trích dẫn. Cập nhật phiên bản là quy trình khác, chưa được triển khai trong importer này.
- Registry lưu `replaces_doc_code` ở văn bản. Metadata ngoài schema bị từ chối để nhóm bổ sung mapping có chủ đích.
- Không thay thế việc kiểm tra OCR, chất lượng nội dung, nguồn gốc, chuyên môn và quyền sử dụng. Các lỗi bị parser chuyển thành null từ trước không thể khôi phục ở backend: phải giữ dữ liệu ngày nguyên gốc đến bước validation.

## Kiểm thử và phạm vi

Từ gốc repo: `python -m pytest -q backend/tests/test_legal_ingestion.py`.

Lệnh trên chạy các ca kiểm thử nhập nguồn, bảo toàn metadata và đối chiếu ID giữa API với tệp Recall. Xem [báo cáo SCRUM-31](../docs/integration/SCRUM-31-VALIDATION.md) để đo thời gian và xuất dữ liệu phân tích cho QA.

Bộ test gồm round-trip database → API, Khoản 1a/0, ngày sai, thời điểm hết hiệu lực, lịch sử kỳ thuế, metadata lệch, duplicate không ghi đè, batch lỗi không ghi dở và rollback. Dữ liệu là fixture giả lập, SQLite riêng. Kiểm tra bổ sung đã chạy parser của Duyên với trích đoạn PDF thật qua PostgreSQL/Docker; xem [bằng chứng tích hợp](../docs/integration/SCRUM-24-POSTGRES.md). Bộ test đơn vị và smoke không thay thế kiểm thử chuyên môn hoặc quy mô pilot.

Không có thay đổi schema database trong bước bổ sung này; migration Khoản dạng chuỗi từ bản sửa trước vẫn phải áp dụng nếu DB cũ chưa được nâng cấp.
