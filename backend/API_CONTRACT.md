# API CONTRACT – Backend ↔ Frontend / AI

Tài liệu mô tả **đúng code hiện tại** của backend (`backend/app/api/v1`, `backend/app/schemas`).
Ví dụ JSON bên dưới lấy từ lần chạy thật ngày 19/11/2026, không viết tay.
Swagger luôn khớp code: http://localhost:8000/docs.

---

## 1. Quy ước chung

| Mục | Quy ước |
|---|---|
| Địa chỉ gốc | `http://localhost:8000/api/v1` (riêng `/health` nằm ngoài `/api/v1`) |
| Định dạng | JSON UTF-8, trừ API xuất Word trả file `.docx` |
| Xác thực | Mọi API (trừ `/health`) cần header `Authorization: Bearer <token>`. Token thử nghiệm: `dev-token-alice-0001` (tổ chức `thtax`), `dev-token-bob-0002` (tổ chức `other`) – cấu hình ở `AUTH_TOKENS` trong `backend/.env` |
| Tổ chức (tenant) | Lấy từ token, **client không gửi**. Mỗi người chỉ thấy hồ sơ của tổ chức mình |
| ID | Hồ sơ, lượt tra cứu: UUID. Đoạn luật (`source_id`): chuỗi số, vd `"1"` |
| Thời gian | `created_at`, `updated_at`, `effective_date`...: ISO 8601 không múi giờ, vd `2026-11-19T14:09:34.206485` |
| Sắc thuế | `VAT` (GTGT), `CIT` (TNDN), `PIT` (TNCN). Giá trị khác → 422 |
| Kỳ thuế | `YYYY`, `YYYY-MM` hoặc `YYYY-Q1..Q4` (vd `2026`, `2026-03`, `2026-Q1`). Sai dạng → 422 |
| CORS | Cho phép `http://localhost:3000`. JS đọc được header `X-Total-Count` và `Content-Disposition` |

### Mã lỗi

Mọi lỗi trả `{"detail": ...}`. `detail` là **chuỗi tiếng Việt** (hiện thẳng cho người dùng), riêng lỗi 422 do sai kiểu dữ liệu là **mảng** các lỗi từng trường.

| Mã | Khi nào | Ví dụ `detail` | Frontend nên |
|---|---|---|---|
| 401 | Thiếu / sai token | `"Chưa đăng nhập hoặc token không hợp lệ"` | Báo cấu hình token |
| 404 | Hồ sơ / lượt tra cứu / nguồn không có **hoặc thuộc tổ chức khác** | `"Không tìm thấy hồ sơ vụ việc"` | Báo không tìm thấy, về danh sách |
| 409 | Ghi vào hồ sơ đã lưu trữ; xuất Word lượt không xuất được | `"Hồ sơ đã lưu trữ, chỉ được xem"` | Hiện `detail` |
| 422 | Dữ liệu gửi lên sai | `"Kỳ thuế cần dạng YYYY, YYYY-MM hoặc YYYY-Q1..Q4."` hoặc mảng `[{"loc": ["body","title"], "msg": "..."}]` | Chuỗi: hiện luôn. Mảng: nối các `msg` |

---

## 2. Danh sách API

| # | Method + đường dẫn | Việc | Thành công |
|---|---|---|---|
| 1 | `POST /matters` | Tạo hồ sơ | 201 `Matter` |
| 2 | `GET /matters` | Danh sách hồ sơ (lọc, phân trang) | 200 `MatterList` |
| 3 | `GET /matters/{id}` | Chi tiết hồ sơ | 200 `Matter` |
| 4 | `PATCH /matters/{id}` | Sửa hồ sơ | 200 `Matter` |
| 5 | `DELETE /matters/{id}` | Lưu trữ hồ sơ (xóa mềm) | 200 `Matter` |
| 6 | `POST /research` | **Tra cứu** trong hồ sơ, tự lưu vào lịch sử | 201 `ResearchResponse` |
| 7 | `GET /matters/{id}/history` | Lịch sử tra cứu của hồ sơ | 200 `HistoryItem[]` |
| 8 | `GET /matters/{id}/history/{history_id}/export` | **Tải báo cáo Word** của 1 lượt tra cứu | 200 file `.docx` |
| 9 | `POST /matters/{id}/history` | Lưu tay 1 lượt tra cứu (không qua tìm kiếm) | 201 `HistoryItem` |
| 10 | `GET /sources/search` | Tìm đoạn luật | 200 `SourceHit[]` |
| 11 | `GET /sources/{source_id}` | Nguyên văn 1 đoạn luật | 200 `SourceDetail` |
| 12 | `GET /health` | Kiểm tra server + DB | 200 |

Ghép với giao diện 3 cột: cột trái = 1, 2, 5; cột giữa = 6, 7, 8; cột phải (xem nguồn) = 10, 11.

---

## 3. Chi tiết từng API

### 3.1 Tạo hồ sơ – `POST /matters` → 201

```json
{ "title": "Khấu trừ VAT đầu vào Q1/2026", "client_name": "Công ty TNHH ABC",
  "description": null, "tax_types": ["VAT"], "tax_period": "2026-Q1" }
```

| Trường | Bắt buộc | Ràng buộc |
|---|---|---|
| `title`, `client_name` | ✔ | 1–255 ký tự, không được toàn dấu cách |
| `description` | | chuỗi |
| `tax_types` | | mảng `VAT`/`CIT`/`PIT`, mặc định `[]` |
| `tax_period` | | tối đa 32 ký tự |

Trả về `Matter`:

```json
{
  "id": "0ae215fc-3c46-4fe3-aa57-29c651f579ff",
  "tenant_id": "thtax",
  "title": "Khấu trừ VAT đầu vào Q1/2026",
  "client_name": "Công ty TNHH ABC",
  "description": null,
  "tax_types": ["VAT"],
  "tax_period": "2026-Q1",
  "status": "active",
  "created_by": "alice",
  "created_at": "2026-11-19T14:09:34.206485",
  "updated_at": "2026-11-19T14:09:34.206488"
}
```

### 3.2 Danh sách hồ sơ – `GET /matters` → 200

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `status` | `active` | `active` \| `archived` \| `all` |
| `q` | | Tìm trong tên hồ sơ **hoặc** tên khách hàng (không phân biệt hoa thường) |
| `limit` | 20 | 1–100 |
| `offset` | 0 | ≥ 0 |

Sắp xếp: hồ sơ cập nhật gần nhất lên đầu.

```json
{ "items": [ { ...Matter... } ], "total": 1, "limit": 20, "offset": 0 }
```

### 3.3 Chi tiết – `GET /matters/{id}` → 200 `Matter`

Không có hoặc thuộc tổ chức khác → 404. `id` không phải UUID → 422.

### 3.4 Sửa – `PATCH /matters/{id}` → 200 `Matter`

Chỉ gửi trường muốn đổi, trường không gửi giữ nguyên.
- `description`, `tax_period` gửi `null` = xóa giá trị.
- `title`, `client_name`, `tax_types` gửi `null` → 422.
- Hồ sơ đã lưu trữ → 409.

### 3.5 Lưu trữ – `DELETE /matters/{id}` → 200 `Matter`

Không xóa thật: `status` thành `"archived"`. Hồ sơ lưu trữ vẫn xem được (3.3, 3.7, 3.8) nhưng **không** sửa, tra cứu hay lưu lịch sử được (409). Gọi lại trên hồ sơ đã lưu trữ vẫn trả 200.

### 3.6 Tra cứu – `POST /research` → 201

Luồng: kiểm tra quyền ghi hồ sơ → lọc và tìm đoạn luật (BM25) → chạy guardrails → **lưu 1 lượt vào lịch sử** → trả kết quả.

```json
{ "matter_id": "0ae215fc-3c46-4fe3-aa57-29c651f579ff",
  "question": "Mức thuế suất 10% áp dụng cho hàng hóa nào?",
  "tax_type": "VAT",
  "tax_period": null,
  "research_as_of": null,
  "material_facts": "Công ty bán máy tính cho doanh nghiệp trong nước",
  "doc_type": null,
  "limit": 10 }
```

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `matter_id` | ✔ | Hồ sơ đang mở |
| `question` | ✔ | 1–2000 ký tự |
| `tax_type` | | Có gửi → **chỉ** tìm văn bản đã gán nhãn sắc thuế đó |
| `tax_period` | | Bỏ trống → dùng kỳ thuế của hồ sơ. Lọc văn bản (và từng đoạn) có hiệu lực trong kỳ |
| `research_as_of` | | Ngày `YYYY-MM-DD`, chỉ dùng khi không có kỳ thuế |
| `material_facts` | | Tình tiết vụ việc. **Thiếu thì guardrails luôn trả `clarify`** |
| `doc_type` | | `LUAT` \| `NGHI_DINH` \| `THONG_TU` \| `CONG_VAN` |
| `limit` | | 1–50, mặc định 10 |

Lỗi: hồ sơ không có / khác tổ chức → 404; hồ sơ đã lưu trữ → 409; kỳ thuế sai dạng → 422.

Trả về `ResearchResponse` (rút gọn):

```json
{
  "history": {
    "id": "29b491a0-2151-414a-aeb7-cbc17be67058",
    "matter_id": "0ae215fc-3c46-4fe3-aa57-29c651f579ff",
    "actor": "alice",
    "question": "Mức thuế suất 10% áp dụng cho hàng hóa nào?",
    "tax_type": "VAT",
    "tax_period": "2026-Q1",
    "research_as_of": null,
    "material_facts": null,
    "answer": null,
    "citations": [
      { "source_id": "1", "title": "Luật Thuế giá trị gia tăng", "legal_identifier": "48/2024/QH15",
        "dieu": "9", "khoan": "3", "diem": null, "url": "https://vbpl.vn/48-2024-qh15" }
    ],
    "warnings": [
      "clarify: missing_context",
      "Vui lòng bổ sung tình huống, giao dịch và đối tượng áp dụng.",
      "Nguồn tìm thấy chưa xác minh đầy đủ hiệu lực, chuyển tiếp và khả năng áp dụng.",
      "Bộ lọc sắc thuế chỉ tìm văn bản đã được gán nhãn; nguồn chưa phân loại bị loại."
    ],
    "research_result": { ...giống research_result bên dưới... },
    "review_status": "draft",
    "answer_version": 1,
    "created_at": "2026-11-19T14:09:34.249266"
  },
  "sources": [ { ...SourceHit, xem 3.10... } ],
  "research_result": {
    "status": "clarify",
    "sections": { "issue": [], "facts": [], "authority": [], "analysis": [], "limitations": [], "next_steps": [] },
    "clarification_questions": ["Vui lòng bổ sung tình huống, giao dịch và đối tượng áp dụng."],
    "warnings": ["missing_context"]
  }
}
```

**Ý nghĩa các trường kết quả:**

| Trường | Ý nghĩa |
|---|---|
| `history` | Bản ghi **đã lưu** vào hồ sơ (giống 1 phần tử của 3.7). Câu hỏi và tình tiết đã được che thông tin cá nhân trước khi lưu |
| `history.answer` | Câu trả lời dạng văn bản. `null` khi chưa có câu trả lời AI |
| `history.citations` | Nguồn trích dẫn. Khi `status = draft` chỉ giữ nguồn AI thực sự dùng; trạng thái khác giữ mọi nguồn tìm được để chuyên viên tự xem |
| `history.warnings` | Cảnh báo để hiển thị: dòng `"<status>: <lý do>"`, câu hỏi cần làm rõ, lưu ý về hiệu lực và bộ lọc |
| `sources` | Mọi đoạn luật tìm được, xếp theo độ liên quan |
| `research_result` | Kết quả 6 phần (xem bảng dưới). Có ở cả `research_result` gốc và `history.research_result` |

**`research_result.status`:**

| Giá trị | Nghĩa | Hiện nay xảy ra khi |
|---|---|---|
| `clarify` | Cần người dùng bổ sung thông tin. Xem `clarification_questions` | Thiếu `material_facts` hoặc thiếu kỳ thuế |
| `abstain` | Hệ thống từ chối trả lời | Không tìm thấy nguồn; hoặc **chưa nối AI** (`assessment_unavailable`) |
| `draft` | Có bản nháp 6 phần, mỗi ý có `citation_ids` trỏ tới `source_id` | Chỉ khi đã nối AI (chưa có) |

`sections` luôn đủ 6 khóa: `issue` (vấn đề pháp lý), `facts` (tình tiết), `authority` (căn cứ), `analysis` (phân tích), `limitations` (giới hạn), `next_steps` (bước tiếp theo). Mỗi khóa là mảng `{ "text": string, "citation_ids": string[] }`.

### 3.7 Lịch sử tra cứu – `GET /matters/{id}/history` → 200 `HistoryItem[]`

- Tham số `limit` (1–100, mặc định 20), `offset`.
- Mới nhất lên đầu. Tổng số lượt nằm ở header **`X-Total-Count`**.
- Mỗi phần tử giống `history` ở 3.6, **có `research_result`** để mở lại hồ sơ vẫn thấy kết quả 6 phần.
- Lượt lưu trước khi có tính năng này, hoặc lưu tay qua 3.9, có `research_result: null`.

### 3.8 Xuất Word – `GET /matters/{id}/history/{history_id}/export` → 200 (file)

Trả file Word của **một lượt tra cứu**, dùng module xuất báo cáo của Quân.

- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Header: `Content-Disposition: attachment; filename="bao-cao-<history_id>.docx"`
- File có tiêu đề "DỰ THẢO – CHƯA ĐƯỢC CHUYÊN GIA PHÊ DUYỆT", 6 phần, câu hỏi cần làm rõ và danh sách nguồn có link.
- Mỗi lần xuất ghi audit log `history.export_docx`.

| Mã | Khi nào |
|---|---|
| 401 | Thiếu token |
| 404 | Hồ sơ khác tổ chức, hoặc `history_id` không thuộc hồ sơ này (kiểm tra **trước** khi tạo file) |
| 409 | Lượt cũ chưa có `research_result` (`"Lượt tra cứu chưa có kết quả 6 phần, hãy tra cứu lại để xuất"`); nguồn được trích dẫn đã bị xóa khỏi kho |
| 422 | Dữ liệu không qua kiểm tra của module Word, vd nguồn không có link `http(s)` |

Vì cần header `Authorization`, **không** mở thẳng link bằng `<a href>`. Tải bằng `fetch` + `blob`:

```ts
export async function downloadReport(matterId: string, historyId: string) {
  const res = await fetch(`${API_URL}/matters/${matterId}/history/${historyId}/export`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Xuất báo cáo thất bại: HTTP ${res.status}`);
  }
  const name = res.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1] ?? `bao-cao-${historyId}.docx`;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
```

### 3.9 Lưu tay lịch sử – `POST /matters/{id}/history` → 201 `HistoryItem`

Dùng khi muốn ghi một lượt mà không qua tìm kiếm (frontend hiện **không** cần, `POST /research` đã tự lưu).
Body: `question` (bắt buộc), `tax_type`, `tax_period`, `research_as_of`, `material_facts`, `answer`, `citations`, `warnings`, `research_result`. Hồ sơ đã lưu trữ → 409.

### 3.10 Tìm đoạn luật – `GET /sources/search` → 200 `SourceHit[]`

| Tham số | Bắt buộc | Ý nghĩa |
|---|---|---|
| `q` | ✔ | Từ khóa / câu hỏi, 1–2000 ký tự |
| `tax_type` | | `VAT`/`CIT`/`PIT` – chỉ văn bản đã gán nhãn |
| `tax_period` | | Kỳ thuế, lọc theo hiệu lực |
| `as_of` | | Ngày `YYYY-MM-DD`, dùng khi không có `tax_period` |
| `doc_type` | | `LUAT` \| `NGHI_DINH` \| `THONG_TU` \| `CONG_VAN` |
| `limit` | | 1–50, mặc định 10 |

Văn bản chưa rõ ngày hiệu lực **không** bị loại (để chuyên viên tự kiểm tra). Không tìm thấy → `[]`.

```json
[
  {
    "source_id": "1",
    "title": "Luật Thuế giá trị gia tăng",
    "legal_identifier": "48/2024/QH15",
    "dieu": "9",
    "khoan": "3",
    "diem": null,
    "url": "https://vbpl.vn/48-2024-qh15",
    "citation_path": "Khoản 3, Điều 9, 48/2024/QH15",
    "doc_type": "LUAT",
    "hierarchy_level": 1,
    "status": "CHUA_XAC_DINH",
    "effective_date": "2025-07-01T00:00:00",
    "expiry_date": null,
    "source_page": 7,
    "version": "1.0",
    "snippet": "Mức thuế suất 10% áp dụng đối với hàng hóa, dịch vụ không quy định tại khoản 1 và khoản 2 Điều này."
  }
]
```

- `hierarchy_level`: 1 Luật > 2 Nghị định > 3 Thông tư > 4 Công văn > 5 Chưa xác định.
- `status` (trạng thái pháp lý): `CHUA_XAC_DINH` \| `CON_HIEU_LUC` \| `HET_HIEU_LUC` \| `SUA_DOI_BO_SUNG` \| `CHUA_CO_HIEU_LUC` \| `BI_THAY_THE`.
- Trạng thái chất lượng OCR và chuyên gia duyệt của nguồn được lưu trong DB nhưng **chưa trả qua API**.

### 3.11 Nguyên văn đoạn luật – `GET /sources/{source_id}` → 200 `SourceDetail`

Giống `SourceHit`, thêm `content` (nguyên văn đầy đủ), `article_title`, `issuer`. Không có → 404.

### 3.12 Sức khỏe – `GET /health` → 200 (không cần token)

```json
{ "status": "ok", "database": true, "version": "0.1.0" }
```
DB lỗi → `"status": "degraded", "database": false`.

---

## 4. Kiểu TypeScript

```ts
export type TaxType = "VAT" | "CIT" | "PIT";
export type ResearchStatus = "draft" | "clarify" | "abstain";
export type SectionName = "issue" | "facts" | "authority" | "analysis" | "limitations" | "next_steps";

export interface Matter {
  id: string; tenant_id: string; title: string; client_name: string;
  description: string | null; tax_types: TaxType[]; tax_period: string | null;
  status: "active" | "archived"; created_by: string; created_at: string; updated_at: string;
}
export interface MatterList { items: Matter[]; total: number; limit: number; offset: number; }
export interface MatterCreate {
  title: string; client_name: string; description?: string | null;
  tax_types?: TaxType[]; tax_period?: string | null;
}
export type MatterUpdate = Partial<MatterCreate>;

export interface Citation {
  source_id: string; title: string | null; legal_identifier: string | null;
  dieu: string | null; khoan: string | null; diem: string | null; url: string | null;
}
export interface SourceHit extends Citation {
  citation_path: string; doc_type: string; hierarchy_level: number; status: string;
  effective_date: string | null; expiry_date: string | null; source_page: number | null;
  version: string | null; snippet: string;
}
export interface SourceDetail extends SourceHit {
  content: string; article_title: string | null; issuer: string | null; version: string;
}

export interface ResearchResult {
  status: ResearchStatus;
  sections: Record<SectionName, { text: string; citation_ids: string[] }[]>;
  clarification_questions: string[];
  warnings: string[];
}
export interface HistoryItem {
  id: string; matter_id: string; actor: string; question: string;
  tax_type: TaxType | null; tax_period: string | null; research_as_of: string | null;
  material_facts: string | null; answer: string | null; citations: Citation[]; warnings: string[];
  research_result: ResearchResult | null;
  review_status: string; answer_version: number; created_at: string;
}
export interface ResearchRequest {
  matter_id: string; question: string; tax_type?: TaxType | null; tax_period?: string | null;
  research_as_of?: string | null; material_facts?: string | null; doc_type?: string | null; limit?: number;
}
export interface ResearchResponse { history: HistoryItem; sources: SourceHit[]; research_result: ResearchResult | null; }
```

---

## 5. Giới hạn hiện tại (để frontend không hiểu nhầm là lỗi)

| Hiện tượng | Lý do | Ai xử lý |
|---|---|---|
| `answer: null`, `research_result.status` là `clarify`/`abstain`, 6 phần trống | Chưa nối AI (bộ đánh giá + bộ sinh câu trả lời) | Nhóm AI (An, Quân) |
| Luôn `clarify: missing_context` | Frontend chưa gửi `material_facts` | Frontend (Phước) |
| Tra cứu không ra nguồn dù có văn bản | Văn bản chưa gán nhãn sắc thuế (`tax_types` khi nạp) | Dữ liệu (Duyên) |
| `status` nguồn luôn `CHUA_XAC_DINH` | Importer chưa ghi trạng thái hiệu lực vào DB | Backend + Dữ liệu |
| `review_status` luôn `draft` | Chưa có API phê duyệt | Sprint sau |
| Chưa có `clarification_scenario`, `case_facts` trong `POST /research` | Nằm ở nhánh SCRUM-32 của An, chưa merge. Khi merge sẽ cập nhật mục 3.6 | AI (An) |

## 6. Khi muốn đổi hợp đồng

1. Sửa schema trong `backend/app/schemas` và test trong `backend/tests`.
2. Sửa tài liệu này (bảng, ví dụ, kiểu TypeScript).
3. Báo frontend (Phước) và AI (An, Quân) trong PR. Thêm trường mới thì client cũ vẫn chạy; đổi tên hoặc xóa trường phải thống nhất trước.
