# 📋 BẢNG PHÂN CÔNG CÔNG VIỆC CHI TIẾT 9 THÀNH VIÊN
## DỰ ÁN: VIETNAM TAX RESEARCH COPILOT WITH CITATIONS (VN-TAX-COPILOT)

* **Khách hàng giả định (RFP):** THTax ([thtax.vn](https://thtax.vn))
* **Mô hình vận hành:** Scrum Agile (8 Sprints / 16 tuần / 5 Cột mốc Gates: G0 ➔ G4)
* **Kho lưu trữ mã nguồn:** [qm041005-design/VN-tax-copilot](https://github.com/qm041005-design/VN-tax-copilot)

---

## 🧭 MA TRẬN TRÁCH NHIỆM TỔNG QUAN (RACI MATRIX)

| STT | Thành viên | Vai trò phụ trách | Nhánh Git cá nhân | Mã yêu cầu RFP chính |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Thành viên 1 | **Product Owner (PO) & Business Analyst** | `feature/01-po-ba-specifications` | `RES-01, RES-03, RES-07, DEL-01` |
| **2** | Thành viên 2 | **Scrum Master (SM) & Process Lead** | `feature/02-scrum-process-templates` | `DEL-04, EVAL-01, EVAL-02` |
| **3** | Thành viên 3 | **Tech Lead & DevOps / Cloud Engineer** | `feature/03-devops-ci-cd-docker` | `ARC-01..05, OPS-01..03, SEC-02` |
| **4** | Thành viên 4 | **Data Engineer 1 (Ingestion & OCR)** | `feature/04-data-ocr-ingestion` | `CIT-05, CIT-06, CIT-07, NFR-04` |
| **5** | Thành viên 5 | **Data Engineer 2 (Legal Registry & Parser)**| `feature/05-data-legal-registry` | `DAT-01, DAT-02, RES-04, RES-05` |
| **6** | Thành viên 6 | **AI / RAG Engineer 1 (Retrieval & Search)** | `feature/06-ai-retrieval-search` | `AI-01, RES-02, EVAL-05, AT-03` |
| **7** | Thành viên 7 | **AI / RAG Engineer 2 (Grounding & Safety)** | `feature/07-ai-grounding-citations` | `AI-02, AI-03, AI-04, SEC-03, VN-03` |
| **8** | Thành viên 8 | **Backend Engineer (API & Matter Services)**| `feature/08-backend-matter-services` | `RES-08, B-01..07, SEC-01, DAT-03` |
| **9** | Thành viên 9 | **Frontend Engineer (UI/UX Workspace)** | `feature/09-frontend-workspace-ui` | `CIT-02, B-05, NFR-05 (WCAG AA)` |

---

## 📝 CHI TIẾT CÔNG VIỆC CỦA TỪNG THÀNH VIÊN

---

### THÀNH VIÊN 1: PRODUCT OWNER (PO) & BUSINESS ANALYST (BA)
* **Nhánh Git:** `feature/01-po-ba-specifications`
* **Mục tiêu chính:** Cầu nối giữa yêu cầu RFP của doanh nghiệp và đội ngũ kỹ thuật; đảm bảo tính chính xác của các quy định thuế Việt Nam.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Quản lý toàn bộ Product Backlog trên Jira, ưu tiên thứ tự làm việc của các tính năng.
  2. Phân tích nghiệp vụ sâu về 3 sắc thuế: **Thuế GTGT (VAT), Thuế TNDN (CIT), Thuế TNCN (PIT)** cùng quy định Hóa đơn điện tử (Nghị định 123/2020 và 70/2025).
  3. Viết User Story chi tiết kèm Tiêu chí chấp nhận (Acceptance Criteria - AC) chuẩn định dạng Gherkin (`Given - When - Then`).
  4. Đại diện nghiệm thu các mốc Release Gates (G0 ➔ G4).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Soạn thảo tài liệu đặc tả phạm vi nghiệp vụ thuế (`docs/rfp/Tax_Scope_Specification.md`).
  * Tạo danh sách 30 câu hỏi tra cứu thuế thực tế thường gặp của doanh nghiệp để làm bài toán mẫu.
  * Phối hợp với QA/AI xây dựng rubric tiêu chí chấm điểm câu trả lời đúng/sai về thuế.
* **Sản phẩm bàn giao (Deliverables):**
  * Bộ User Stories hoàn chỉnh trên Jira cho Sprint 1 & Sprint 2.
  * Tài liệu `SRS_Tax_Scope.md` được lưu trong Git.

---

### THÀNH VIÊN 2: SCRUM MASTER (SM) & QUALITY ASSURANCE (QA) LEAD
* **Nhánh Git:** `feature/02-scrum-process-templates`
* **Mục tiêu chính:** Vận hành trơn tru quy trình Agile/Scrum, gỡ bỏ trở ngại (blockers) cho 9 thành viên, quản lý chất lượng kiểm thử nghiệm thu.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Điều phối các buổi họp Scrum: Daily Standup (10-15 phút hàng ngày), Sprint Planning, Sprint Review và Sprint Retrospective.
  2. Quản lý chỉ số vận hành nhóm trên Jira: Burndown chart, Velocity, Cumulative Flow Diagram.
  3. Xây dựng và giám sát Định nghĩa hoàn thành (**Definition of Done - DoD**) và Định nghĩa sẵn sàng (**Definition of Ready - DoR**).
  4. Quản lý bộ dữ liệu Benchmark kiểm thử chất lượng (200 câu hỏi trả lời được + 50 câu hỏi bẫy/mơ hồ theo phụ lục Annex E).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Cấu hình Jira Scrum Board (Workflow: `Backlog ➔ Selected ➔ In Progress ➔ PR Review ➔ QA Testing ➔ Done`).
  * Soạn thảo tài liệu `docs/scrum/SCRUM_AGREEMENT.md` quy định giờ họp, cách chấm điểm và quy tắc team.
  * Thiết lập bảng theo dõi 60 ca kiểm thử đặc thù Việt Nam (`VN 06` - OCR hỏng, văn bản hết hạn, xung đột công văn).
* **Sản phẩm bàn giao (Deliverables):**
  * Bảng Jira Board sẵn sàng cho 9 người sử dụng.
  * Biên bản họp Sprint 1 Planning & DoD Checklist.
  * Tập dữ liệu test ban đầu (`evaluation/datasets/seed_questions.json`).

---

### THÀNH VIÊN 3: TECH LEAD & DEVOPS / CLOUD ENGINEER
* **Nhánh Git:** `feature/03-devops-ci-cd-docker`
* **Mục tiêu chính:** Thiết kế kiến trúc tổng thể của hệ thống, quản lý hạ tầng Docker, CI/CD pipeline và đảm bảo an ninh mạng.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Duy trì và mở rộng môi trường Docker Compose / Kubernetes cho toàn bộ team dev.
  2. Xây dựng GitHub Actions tự động kiểm tra code (Linting, Type check, Unit test) mỗi khi có Pull Request vào `develop`.
  3. Thiết lập hệ thống Logging tập trung, giám sát chi phí token LLM và đo lường độ trễ (Latency p95 < 30s).
  4. Phụ trách bảo mật: Quản lý biến môi trường (`.env`), không lộ API Keys, thiết lập ranh giới bảo mật (Trust Boundaries - ARC 01).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Hoàn thiện môi trường container hóa trong `docker-compose.yml`: Database (PostgreSQL 16 + pgvector), Backend, Frontend.
  * Cấu hình GitHub Actions CI pipeline cơ bản (`.github/workflows/ci.yml`).
  * Vẽ sơ đồ kiến trúc hệ thống (System Architecture Diagram chuẩn C4 model) lưu trong `docs/architecture/`.
* **Sản phẩm bàn giao (Deliverables):**
  * Môi trường local chạy mượt mà với 1 lệnh `docker compose up --build`.
  * GitHub Actions CI hoạt động, chặn merge khi test fail.
  * Tài liệu `docs/architecture/ARCHITECTURE.md`.

---

### THÀNH VIÊN 4: DATA ENGINEER 1 (INGESTION & VIETNAMESE OCR)
* **Nhánh Git:** `feature/04-data-ocr-ingestion`
* **Mục tiêu chính:** Xây dựng phễu thu thập văn bản pháp luật và pipeline xử lý OCR tiếng Việt chất lượng cao từ các bản scan/PDF.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Thu thập dữ liệu các văn bản quy phạm pháp luật Thuế từ Cổng thông tin điện tử Chính phủ, Công báo, Tổng cục Thuế.
  2. Xử lý OCR tiếng Việt cho các tài liệu dạng scan/ảnh (sử dụng PaddleOCR, Tesseract, hoặc Google Cloud Document AI).
  3. Bảo toàn chính xác 100% tiếng Việt có dấu (Unicode NFC), giữ nguyên cấu trúc bảng biểu, số tiền, ngày tháng và công thức.
  4. Xây dựng cơ chế phát hiện và cách ly tài liệu lỗi (Quarantine failed OCR - yêu cầu `CIT 06`).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Tải và phân loại tập dữ liệu văn bản nền tảng gồm các Luật Thuế mới nhất: Luật 48/2024/QH15 (VAT), Luật 67/2025/QH15 (TNDN), Luật 109/2025/QH15 (TNCN).
  * Viết script Python OCR tự động chuyển PDF scan sang dạng text sạch có đánh dấu số trang gốc (`original_page`).
  * Đánh giá độ chính xác của OCR trên 50 trang scan mẫu (yêu cầu nhận diện đúng dấu tiếng Việt và chữ số).
* **Sản phẩm bàn giao (Deliverables):**
  * Module `data_pipeline/ocr/` hoàn chỉnh.
  * Thư mục văn bản gốc đã OCR sạch lưu trữ theo chuẩn cấu trúc.

---

### THÀNH VIÊN 5: DATA ENGINEER 2 (LEGAL REGISTRY & CHUNKING PARSER)
* **Nhánh Git:** `feature/05-data-legal-registry`
* **Mục tiêu chính:** Quản trị CSDL văn bản pháp điển, siêu dữ liệu (Metadata) và bóc tách cấu trúc theo Điều - Khoản - Điểm.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Thiết kế Schema cơ sở dữ liệu pháp luật theo chuẩn RFP:
     * Bảng Văn bản (`DAT 01` - Source Record): `source_id`, số hiệu, cơ quan ban hành, loại văn bản, ngày hiệu lực, ngày hết hiệu lực, liên kết sửa đổi.
     * Bảng Đoạn trích (`DAT 02` - Passage Record): `passage_id`, `article_or_section` (Điều), `paragraph` (Khoản), `point` (Điểm), nội dung trích đoạn.
  2. Viết bộ Parser chia nhỏ văn bản (Legal Chunking): Phải cắt theo cấu trúc ngữ nghĩa pháp lý (Điều/Khoản/Điểm), tuyệt đối không cắt thô thiển theo độ dài token.
  3. Xây dựng cơ chế phân biệt thứ bậc hiệu lực pháp lý (Legal Hierarchy): Phân biệt rõ Luật > Nghị định > Thông tư > Công văn hành chính cá biệt (`RES 04`, `VN 02`).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Định nghĩa schema database trên PostgreSQL / SQLAlchemy ORM.
  * Viết script regex parser bóc tách thành công văn bản mẫu thành danh sách các record dạng JSON cấu trúc Điều/Khoản/Điểm.
  * Xây dựng từ điển ánh xạ viết tắt ngành thuế: GTGT, TNDN, TNCN, MST, HĐĐT (`VN 01`).
* **Sản phẩm bàn giao (Deliverables):**
  * Module `data_pipeline/parser/legal_chunker.py`.
  * File database seed chứa 10 văn bản luật cốt lõi đã được bóc tách hoàn chỉnh Điều/Khoản.

---

### THÀNH VIÊN 6: AI / RAG ENGINEER 1 (RETRIEVAL & HYBRID SEARCH)
* **Nhánh Git:** `feature/06-ai-retrieval-search`
* **Mục tiêu chính:** Xây dựng hệ thống truy hồi thông tin (Search Engine) chính xác tuyệt đối, kết hợp tìm kiếm từ khóa và tìm kiếm ngữ nghĩa.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Cài đặt mô hình tìm kiếm từ khóa chính xác BM25 (đảm bảo tìm đúng số hiệu nghị định, số điều, thuật ngữ thuế đặc thù).
  2. Cài đặt mô hình Vector Embedding tiếng Việt chất lượng cao (ví dụ: `bkai-foundation-models/vietnamese-bi-encoder`, `bge-m3` hoặc `text-embedding-3`).
  3. Xây dựng Hybrid Search (kết hợp điểm BM25 + Dense Vector bằng thuật toán Reciprocal Rank Fusion - RRF).
  4. Tích hợp Reranker (Cross-encoder) để sắp xếp lại top kết quả liên quan nhất.
  5. Đạt chỉ tiêu đo lường: **Recall@10 ≥ 90%** trên 200 câu hỏi test benchmark (`AT 03`, `EVAL 05`).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Thử nghiệm vector hóa các đoạn trích Điều/Khoản vào cơ sở dữ liệu `pgvector`.
  * Viết hàm tìm kiếm cơ bản nhận vào câu hỏi và trả về Top 5 Điều luật liên quan nhất.
  * Xây dựng bộ lọc Metadata: Cho phép lọc theo sắc thuế (VAT/CIT/PIT) và năm áp dụng trước khi tìm kiếm.
* **Sản phẩm bàn giao (Deliverables):**
  * Module `ai_engine/retrieval/hybrid_search.py`.
  * Notebook thực nghiệm so sánh độ chính xác giữa BM25 đơn thuần và Hybrid Search.

---

### THÀNH VIÊN 7: AI / RAG ENGINEER 2 (GROUNDED GENERATION & SAFETY GUARDRAILS)
* **Nhánh Git:** `feature/07-ai-grounding-citations`
* **Mục tiêu chính:** Xây dựng khối tổng hợp câu trả lời của AI, chống bịa đặt (Anti-Hallucination), kiểm tra trích dẫn và bảo mật dữ liệu.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Kỹ thuật Prompt Engineering: Ép LLM trả lời theo cấu trúc chuẩn nghiệp vụ thuế (Nhận định ➔ Căn cứ pháp lý ➔ Phân tích ➔ Lưu ý loại trừ).
  2. Buộc LLM gắn nhãn trích dẫn chi tiết (Pinpoint Citation) dạng: `[Điều X, Khoản Y, Luật Z]` ngay sau mỗi khẳng định.
  3. Xây dựng module **Citation Validator** (`AI 03`): Đối soát tự động xem điều luật mà LLM trích dẫn có thực sự tồn tại trong cơ sở dữ liệu hay không.
  4. Xây dựng cơ chế từ chối trả lời (**Abstention** - `AI 04`): Khi dữ liệu thiếu, mâu thuẫn hoặc câu hỏi nằm ngoài phạm vi thuế, AI phải từ chối hoặc yêu cầu làm rõ chứ không được đoán mò.
  5. Xây dựng bộ lọc che giấu thông tin cá nhân (**Data Redaction** - `VN 03`): Tự động che số CCCD, mã số thuế cá nhân, tiền lương trước khi gửi ra ngoài, tuân thủ Luật Bảo vệ dữ liệu cá nhân (PDPD).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Soạn thảo System Prompt cốt lõi cho Copilot có trích dẫn nguồn.
  * Viết module Redaction bằng regex để ẩn số CMND/CCCD, MST cá nhân.
  * Thiết kế kịch bản test thử nghiệm bẫy xem LLM có bị hallucinate khi gặp câu hỏi không có căn cứ hay không.
* **Sản phẩm bàn giao (Deliverables):**
  * Module `ai_engine/synthesis/prompt_templates.py` và `ai_engine/guardrails/redaction.py`.
  * Tài liệu đánh giá rủi ro an toàn AI (`docs/rfp/AI_Safety_Card.md`).

---

### THÀNH VIÊN 8: BACKEND ENGINEER (APIS & MATTER WORKSPACE)
* **Nhánh Git:** `feature/08-backend-matter-services`
* **Mục tiêu chính:** Xây dựng toàn bộ hệ thống API phục vụ giao diện, quản lý người dùng, hồ sơ vụ việc nghiên cứu thuế (Matter Workspace) và xuất báo cáo.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Xây dựng RESTful API bằng FastAPI (Python) hoặc Node.js (TypeScript).
  2. Quản lý hồ sơ vụ việc khách hàng (**Matter Workspace** - `RES 08`): Tạo mới vụ việc, lưu lịch sử trao đổi, cách ly dữ liệu giữa các khách hàng (Tenant & Matter Isolation - `SEC 01`).
  3. Quản lý trạng thái thẩm định (**Review Workflow**): Chuyển đổi trạng thái câu trả lời từ `Draft` ➔ `In Review` ➔ `Approved` / `Rejected`.
  4. Xây dựng module xuất báo cáo chuyên nghiệp ra định dạng **Word (.DOCX)** và **PDF** có kèm danh mục trích dẫn luật sống (`B 05`).
  5. Ghi vết kiểm toán (**Audit Logging** - `DAT 04`): Lưu lại ai đã tra cứu, ai đã duyệt câu trả lời, thời gian UTC.
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Dựng khung ứng dụng FastAPI hoàn chỉnh, tích hợp kết nối CSDL PostgreSQL.
  * Cài đặt tài liệu Swagger API tự động (`/docs`).
  * Viết các API CRUD đầu tiên: Quản lý hồ sơ vụ việc (`/api/v1/matters`) và API tra cứu thử nghiệm (`/api/v1/research`).
* **Sản phẩm bàn giao (Deliverables):**
  * Mã nguồn backend trong thư mục `backend/app/`.
  * Bộ kiểm thử Unit Test cho API với độ phủ > 80%.

---

### THÀNH VIÊN 9: FRONTEND ENGINEER (UI/UX & WORKSPACE INTERFACE)
* **Nhánh Git:** `feature/09-frontend-workspace-ui`
* **Mục tiêu chính:** Xây dựng giao diện ứng dụng Web trực quan, thân thiện cho chuyên gia thuế, hỗ trợ xem trích dẫn văn bản gốc và đáp ứng chuẩn tiếp cận WCAG 2.2 AA.
* **Nhiệm vụ xuyên suốt dự án:**
  1. Phát triển Web App bằng Next.js / React và TailwindCSS.
  2. Màn hình Nghiên cứu (Research Workspace): Chat tương tác với Copilot, bộ lọc sắc thuế (GTGT, TNDN, TNCN) và chọn năm tính thuế.
  3. Màn hình Xem trước văn bản gốc (**Citation Drawer / Preview** - `CIT 02`): Khi người dùng bấm vào một nhãn trích dẫn `[Điều 14]`, bên phải sẽ trượt ra một khung hiển thị nguyên văn đoạn trích và nút mở văn bản gốc.
  4. Màn hình Thẩm định & Phê duyệt (**Review Dashboard**): Cho phép chuyên gia thuế sửa chữa câu trả lời, bấm "Approve" hoặc "Reject", và bấm nút "Xuất file DOCX".
  5. Đảm bảo giao diện chuẩn tiếp cận WCAG 2.2 AA (phím tắt điều hướng, độ tương phản màu sắc, nhãn rõ ràng).
* **Nhiệm vụ cụ thể Sprint 1 & 2 (Tuần 1 - Tuần 4 | Mốc G0 ➔ G1):**
  * Dựng khung ứng dụng Next.js trong thư mục `frontend/`.
  * Dựng layout 3 cột chuẩn:
    * Cột trái: Danh sách vụ việc (Matters).
    * Cột giữa: Khung chat hỏi đáp AI & bộ lọc sắc thuế.
    * Cột phải: Component Drawer xem trước trích dẫn nguồn.
  * Kết nối giao diện với API Backend mẫu.
* **Sản phẩm bàn giao (Deliverables):**
  * Ứng dụng web chạy được tại `http://localhost:3000`.
  * Bộ UI Component hoàn chỉnh phục vụ cho demo mốc G1.

---

## 🤝 QUY CHẾ PHỐI HỢP CẶP ĐÔI (PAIRING & CROSS-COLLABORATION)

Để đảm bảo dự án không bị đứt gãy giữa các bộ phận, 9 thành viên sẽ bắt cặp hỗ trợ chéo:
1. **PO (1) ⟷ QA/Scrum Master (2):** Đảm bảo mỗi User Story đều có tiêu chí Acceptance Criteria rõ ràng và có test case tương ứng.
2. **Data Eng 1 (4) ⟷ Data Eng 2 (5):** Đảm bảo đầu ra của module OCR khớp chính xác với đầu vào của bộ chia nhỏ Điều/Khoản.
3. **AI Search (6) ⟷ AI Safety (7):** Đảm bảo văn bản truy hồi được từ Search được đưa vào Prompt tổng hợp và đối soát trích dẫn không bị lỗi.
4. **Backend (8) ⟷ Frontend (9):** Thống nhất chuẩn OpenAPI (JSON schema) trước khi code để giao diện và API khớp nhau ngay từ đầu.
5. **Tech Lead (3):** Hỗ trợ kỹ thuật cho tất cả các nhánh, phụ trách review code và duyệt Pull Request merge vào `develop`.
