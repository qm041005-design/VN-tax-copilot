# SCRUM-24 — nhận dữ liệu parser trước khi lưu

`app.services.legal_ingestion_service.ingest_legal_document(db, payload)` là hàm nội bộ, không phải endpoint công khai. Chỉ gọi từ quy trình nhập nguồn công khai đã kiểm tra quyền sử dụng. Caller quản lý transaction và commit/rollback; không cấp khả năng ghi nguồn cho người dùng tra cứu.

## Cách gọi

```python
from app.core.database import SessionLocal
from app.services.legal_ingestion_service import ingest_legal_document

# document_metadata: doc_code, title, doc_type, hierarchy_level,
# issue_date/effective_date/expiry_date, source_url, version, issuer nếu có.
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

## Quy ước

- Ngày hợp lệ: chuỗi YYYY-MM-DD, Python date hoặc datetime không timezone tại 00:00:00 (tương thích parser). Giá trị thiếu là null hoặc không gửi trường.
- Chuỗi rỗng, `invalid`, ngày không tồn tại, timestamp dạng số, chuỗi datetime có timezone hoặc datetime có giờ đều bị từ chối. Không tự bỏ giờ/múi giờ hoặc chuyển dữ liệu lỗi thành null.
- Khoảng hiệu lực là `[effective_date, expiry_date)`. Ngày kết thúc phải sau ngày bắt đầu; bằng nhau là khoảng rỗng, bị chặn. Đúng ngày hết hiệu lực trở đi trả HET_HIEU_LUC. Văn bản hết hiệu lực vẫn được lưu để nghiên cứu lịch sử.
- Ngày thiếu không bị suy đoán. `temporal_status` trong receipt chỉ suy ra từ ngày, chưa chứng minh văn bản còn hiệu lực pháp lý hoặc áp dụng được cho một vụ việc. Không lưu status do parser tự đưa vào như quyết định đã duyệt.
- Giữ Điều/Khoản `1a`. Số 0, chuỗi "0", rỗng/null của Khoản được chuẩn hóa; DB dùng sentinel "0" để tương thích registry, API trả null.
- Metadata ngày, URL, version, loại và thứ bậc ở đoạn nếu được cung cấp phải khớp văn bản; trường không cung cấp có thể kế thừa. Không dùng tham số ORM `**chunk` vì parser có các trường khác model. Giữ nguyên content đã chứa phần mở đầu Điều/Khoản; các trường intro riêng không có cột backend nên không lưu riêng.
- Mã văn bản đã tồn tại bị từ chối; không thay nội dung đằng sau một ID đã được trích dẫn. Cập nhật phiên bản là quy trình khác, chưa được triển khai trong importer này.
- Quan hệ `replaces_doc_code` có giá trị chưa được hỗ trợ lưu nên bị chặn rõ ràng; không bỏ dữ liệu thay thế âm thầm. Metadata ngoài schema bị từ chối để nhóm bổ sung mapping có chủ đích.
- Không thay thế việc kiểm tra OCR, chất lượng nội dung, nguồn gốc, chuyên môn và quyền sử dụng. Các lỗi bị parser chuyển thành null từ trước không thể khôi phục ở backend: phải giữ dữ liệu ngày nguyên gốc đến bước validation.

## Kiểm thử và phạm vi

Từ gốc repo: `python -m pytest -q backend/tests/test_legal_ingestion.py`.

Bộ test gồm round-trip database → API, Khoản 1a/0, ngày sai, thời điểm hết hiệu lực, lịch sử kỳ thuế, metadata lệch, duplicate không ghi đè, batch lỗi không ghi dở và rollback. Dữ liệu là fixture giả lập, SQLite riêng. Kiểm tra bổ sung đã chạy parser của Duyên với trích đoạn PDF thật qua PostgreSQL/Docker; xem [bằng chứng tích hợp](../docs/integration/SCRUM-24-POSTGRES.md). Bộ test đơn vị và smoke không thay thế kiểm thử chuyên môn hoặc quy mô pilot.

Không có thay đổi schema database trong bước bổ sung này; migration Khoản dạng chuỗi từ bản sửa trước vẫn phải áp dụng nếu DB cũ chưa được nâng cấp.
