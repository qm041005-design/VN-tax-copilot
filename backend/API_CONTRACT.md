# 📄 API CONTRACT – Hợp đồng dữ liệu giữa Backend và Frontend

## 0. "API contract" là gì? Vì sao cần?

Backend (nhóm 8) và Frontend (nhóm 9) làm song song trên 2 nhánh khác nhau. Để khi ghép lại **chạy được ngay**, hai bên phải thống nhất trước:

- Gọi **địa chỉ nào** (URL, method GET/POST/…)
- **Gửi gì** lên (header, tham số, JSON body – tên trường, kiểu dữ liệu)
- **Nhận gì** về (JSON trả về, mã lỗi khi sai)

Bản thống nhất đó gọi là **hợp đồng API**. Giống hợp đồng thật: bên nào muốn đổi (đổi tên trường, thêm/bớt trường) thì **phải báo bên kia và sửa file này trước**, nếu không frontend sẽ hỏng âm thầm (hiện `undefined`, lỗi trắng trang).

Nguồn tham chiếu kỹ thuật luôn đúng với code: Swagger http://localhost:8000/docs (phần **Schemas** ở cuối trang) và `/openapi.json`.

> **Trạng thái:** bản đề xuất của backend – chờ nhóm 9 xác nhận. Có góp ý thì sửa file này + comment trên Jira SCRUM-24.

---

## 1. Quy ước chung

| Mục | Quy ước |
|---|---|
| Địa chỉ gốc (local) | `http://localhost:8000/api/v1` |
| Xác thực | Mọi request gửi header `Authorization: Bearer <token>`. Token thử nghiệm: `dev-token-alice-0001` |
| Định dạng | JSON UTF-8, tên trường kiểu `snake_case` (vd `client_name`, không phải `clientName`) |
| Thời gian | Chuỗi ISO 8601 giờ UTC, vd `"2026-11-13T10:28:17Z"` → frontend tự đổi sang giờ Việt Nam |
| Ngày | `"YYYY-MM-DD"`, vd `"2026-03-15"` |
| ID | Hồ sơ, lịch sử: UUID (chuỗi). Nguồn luật (`source_id`): chuỗi số, vd `"42"` |
| Sắc thuế | Chỉ nhận `"VAT"` (GTGT), `"CIT"` (TNDN), `"PIT"` (TNCN) |
| Trường không có giá trị | Trả `null` (không bỏ trường) |

### Mã lỗi – frontend xử lý thế nào

| Mã | Nghĩa | Frontend nên |
|---|---|---|
| 200 / 201 | Thành công / đã tạo | Hiển thị dữ liệu |
| **401** | Thiếu hoặc sai token | Báo "Chưa đăng nhập" |
| **404** | Không có, hoặc thuộc tổ chức khác | Báo "Không tìm thấy hồ sơ" |
| **409** | Hồ sơ đã lưu trữ, chỉ được xem | Khóa ô chat / nút sửa |
| **422** | Dữ liệu gửi lên sai | Hiển thị lỗi cạnh ô nhập |

Thân lỗi luôn có trường `detail`:
```json
{"detail": "Không tìm thấy hồ sơ vụ việc"}
```
Riêng 422, `detail` là một mảng, mỗi phần tử chỉ ra trường sai:
```json
{"detail": [{"loc": ["body", "title"], "msg": "String should have at least 1 character", "type": "string_too_short"}]}
```

---

## 2. Bản đồ API theo 3 cột giao diện

| Cột | Việc | Method + đường dẫn |
|---|---|---|
| 1 – Hồ sơ | Danh sách, tìm hồ sơ | `GET /matters?status=active&q=&limit=20&offset=0` |
| 1 | Tạo hồ sơ | `POST /matters` |
| 1 | Xem / sửa / lưu trữ hồ sơ | `GET` / `PATCH` / `DELETE /matters/{id}` |
| 2 – Chat | Gửi câu hỏi (tự lưu lịch sử) | `POST /research` |
| 2 | Tải lịch sử chat của hồ sơ | `GET /matters/{id}/history?limit=20&offset=0` |
| 3 – Trích dẫn | Mở nguyên văn đoạn luật khi bấm vào trích dẫn | `GET /sources/{source_id}` |
| 3 | Tìm đoạn luật tự do | `GET /sources/search?q=&doc_type=&as_of=&limit=10` |

---

## 3. Chi tiết từng API (kèm ví dụ thật)

### 3.1 Tạo hồ sơ – `POST /matters` → 201
Gửi:
```json
{"title": "Khấu trừ VAT Q1/2026", "client_name": "Công ty ABC", "description": null, "tax_types": ["VAT"], "tax_period": "2026"}
```
`title`, `client_name` bắt buộc (không được rỗng, tối đa 255 ký tự); còn lại tùy chọn.

Nhận (**Matter**):
```json
{
  "id": "d6e2e043-31f4-4de9-9e35-b451ef596eeb",
  "tenant_id": "thtax",
  "title": "Khấu trừ VAT Q1/2026",
  "client_name": "Công ty ABC",
  "description": null,
  "tax_types": ["VAT"],
  "tax_period": "2026",
  "status": "active",
  "created_by": "alice",
  "created_at": "2026-11-13T10:28:17Z",
  "updated_at": "2026-11-13T10:28:17Z"
}
```

### 3.2 Danh sách hồ sơ – `GET /matters` → 200
Tham số: `status` = `active` (mặc định) | `archived` | `all`; `q` = tìm theo tên hồ sơ/khách hàng; `limit` (1–100), `offset`.
```json
{"items": [ /* các Matter như 3.1 */ ], "total": 1, "limit": 20, "offset": 0}
```

### 3.3 Sửa hồ sơ – `PATCH /matters/{id}` → 200
Chỉ gửi trường muốn đổi: `{"title": "Tên mới"}`. Gửi `null` cho `description`/`tax_period` = xóa giá trị. Hồ sơ đã lưu trữ → 409.

### 3.4 Lưu trữ hồ sơ – `DELETE /matters/{id}` → 200
Không xóa thật, trả Matter với `"status": "archived"`.

### 3.5 Gửi câu hỏi – `POST /research` → 201
Gửi:
```json
{"matter_id": "d6e2e043-...", "question": "Thuế suất GTGT phổ thông là bao nhiêu?", "tax_type": "VAT", "research_as_of": "2026-03-15"}
```
| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `matter_id` | Có | Hồ sơ đang mở |
| `question` | Có | Câu hỏi (1–2000 ký tự) |
| `tax_type` | Không | `VAT` / `CIT` / `PIT` |
| `tax_period` | Không | Kỳ thuế; bỏ trống thì lấy của hồ sơ |
| `research_as_of` | Không | Chỉ lấy luật còn hiệu lực tại ngày này |
| `material_facts` | Không | Tình tiết bổ sung |
| `doc_type` | Không | Chỉ tìm trong `LUAT` / `NGHI_DINH` / `THONG_TU` / `CONG_VAN` |
| `limit` | Không | Số nguồn tối đa (1–50, mặc định 10) |

Nhận:
```json
{
  "history": {
    "id": "7a7074e5-...",
    "matter_id": "d6e2e043-...",
    "actor": "alice",
    "question": "Thuế suất GTGT phổ thông là bao nhiêu?",
    "tax_type": "VAT",
    "tax_period": "2026",
    "research_as_of": "2026-03-15",
    "material_facts": null,
    "answer": null,
    "citations": [
      {"source_id": "42", "title": "Luật Thuế giá trị gia tăng", "legal_identifier": "48/2024/QH15",
       "dieu": "9", "khoan": "3", "diem": "a", "url": "https://..."}
    ],
    "warnings": ["Chưa có câu trả lời AI; danh sách trích dẫn là căn cứ tìm được, chuyên viên cần tự đối chiếu."],
    "review_status": "draft",
    "answer_version": 1,
    "created_at": "2026-11-13T10:30:00Z"
  },
  "sources": [ /* SourceHit – xem 3.7, cùng thứ tự với history.citations */ ]
}
```
- `answer` hiện **luôn `null`** (chưa nối AI) → frontend hiển thị `warnings[0]` trong bong bóng trả lời.
- Không tìm thấy nguồn: `citations: []`, `sources: []`, `warnings[0]` = "Không tìm thấy căn cứ pháp lý phù hợp…".

### 3.6 Lịch sử chat – `GET /matters/{id}/history` → 200
Trả **mảng** các `history` như 3.5 (mới nhất trước). Tổng số bản ghi nằm ở **header** `X-Total-Count` (dùng để phân trang).

### 3.7 Tìm đoạn luật – `GET /sources/search?q=thuế suất&as_of=2026-03-15` → 200
Trả mảng **SourceHit** (xếp theo độ khớp, rồi Luật trước Nghị định trước Thông tư trước Công văn):
```json
[{
  "source_id": "42",
  "title": "Luật Thuế giá trị gia tăng",
  "legal_identifier": "48/2024/QH15",
  "dieu": "9", "khoan": "3", "diem": "a",
  "url": "https://...",
  "citation_path": "Điểm a, Khoản 3, Điều 9, 48/2024/QH15",
  "doc_type": "LUAT",
  "hierarchy_level": 1,
  "effective_date": "2025-07-01T00:00:00",
  "expiry_date": null,
  "snippet": "300 ký tự đầu của đoạn luật..."
}]
```

### 3.8 Nguyên văn đoạn luật – `GET /sources/{source_id}` → 200
Trả **SourceDetail** = mọi trường của SourceHit, thêm:
```json
{"content": "Toàn văn đoạn luật...", "article_title": "Thuế suất", "issuer": "Quốc hội", "version": "1.0", "source_page": 5}
```

---

## 4. Kiểu TypeScript (dán vào `frontend/src/services/types.ts`)
```ts
export type TaxType = "VAT" | "CIT" | "PIT";

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
  citation_path: string;
  doc_type: string;                      // LUAT | NGHI_DINH | THONG_TU | CONG_VAN
  hierarchy_level: number;               // 1 Luật > 2 Nghị định > 3 Thông tư > 4 Công văn
  effective_date: string | null; expiry_date: string | null;
  snippet: string;
}
export interface SourceDetail extends SourceHit {
  content: string; article_title: string | null; issuer: string | null;
  version: string; source_page: number | null;
}

export interface HistoryItem {
  id: string; matter_id: string; actor: string; question: string;
  tax_type: TaxType | null; tax_period: string | null; research_as_of: string | null;
  material_facts: string | null; answer: string | null;
  citations: Citation[]; warnings: string[];
  review_status: "draft" | "under_review" | "approved" | "rejected" | "superseded";
  answer_version: number; created_at: string;
}
export interface ResearchRequest {
  matter_id: string; question: string; tax_type?: TaxType; tax_period?: string;
  research_as_of?: string; material_facts?: string; doc_type?: string; limit?: number;
}
export interface ResearchResponse { history: HistoryItem; sources: SourceHit[]; }
```

---

## 5. Đổi dữ liệu giả của frontend sang dữ liệu thật

Frontend hiện (`frontend/src/app/page.tsx`) dùng dữ liệu mẫu với tên trường khác. Khi nối API, đổi như sau:

| Frontend đang dùng | Lấy từ backend | Cách hiển thị |
|---|---|---|
| `matter.id` (`MT-2026-001`) | `id` (UUID) | Muốn mã ngắn: 8 ký tự đầu của UUID |
| `matter.name` | `title` | |
| `matter.company` | `client_name` | |
| `matter.tax` (1 giá trị) | `tax_types` (mảng) | `tax_types.join(", ")` |
| `matter.updated` ("10 phút trước") | `updated_at` | Tự đổi sang thời gian tương đối |
| `matter.status` (Đang xử lý / Chờ duyệt / Đã duyệt) | `review_status` của lượt tra cứu mới nhất | `draft`→Đang xử lý · `under_review`→Chờ duyệt · `approved`→Đã duyệt |
| Bộ lọc năm | `tax_period`, `research_as_of` | |
| Tin nhắn chat | mỗi `HistoryItem` = 1 tin user (`question`) + 1 tin trợ lý (`answer` hoặc `warnings[0]`) | |
| Khung trích dẫn `LegalContent` | `GET /sources/{source_id}` | `title`←`article_title`, `number`←`legal_identifier`, `law`←`title`, `article`←`content` |

---

## 6. Ví dụ code `fetch`
```ts
const API = "http://localhost:8000/api/v1";
const TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "dev-token-alice-0001"; // chỉ cho môi trường thử nghiệm
const headers = { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(JSON.stringify((await res.json()).detail));
  return res.json();
}

const matters = await call<MatterList>("/matters");
const { history, sources } = await call<ResearchResponse>("/research", {
  method: "POST",
  body: JSON.stringify({ matter_id: matters.items[0].id, question: "Thuế suất GTGT phổ thông?" }),
});
```

---

## 7. Quy trình khi muốn đổi hợp đồng
1. Bên muốn đổi ghi đề xuất vào Jira SCRUM-24 (hoặc nhóm chat).
2. Sửa file này + sửa code (`app/schemas/*.py` ở backend, `types.ts` ở frontend).
3. Bên kia xác nhận rồi mới merge vào `develop`.
