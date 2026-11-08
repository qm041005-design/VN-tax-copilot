# 📋 BẢNG PHÂN CHIA VAI TRÒ & NHIỆM VỤ KỸ THUẬT (DÀNH CHO DÂN CNTT)
## DỰ ÁN: VIETNAM TAX RESEARCH COPILOT WITH CITATIONS (VN-TAX-COPILOT)

* **Repository:** [qm041005-design/VN-tax-copilot](https://github.com/qm041005-design/VN-tax-copilot)
* **Phương pháp luận:** Scrum Agile (8 Sprints / 16 tuần)
* **Đặc thù nhóm:** 9 thành viên chuyên ngành Công nghệ thông tin / Kỹ thuật phần mềm.
* **Tiêu chí phân bổ:** Đảm bảo **100% thành viên đều có mã nguồn (code) cụ thể trên GitHub**, có Pull Request và đóng góp kỹ thuật rõ ràng để bảo vệ đồ án trước hội đồng giảng viên.

---

## 🎯 BẢNG TỔNG HỢP 9 VAI TRÒ KỸ THUẬT

| STT | Vai trò (Chức danh CNTT) | Công nghệ / Ngôn ngữ | Module Code chịu trách nhiệm trên GitHub | Nhánh Git |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **BA & Prompt Engineer** | Python, Jinja2, python-docx | `ai_engine/synthesis/`, `backend/app/services/export_service.py` | `feature/01-po-ba-specifications` |
| **2** | **Scrum Master & Automation QA** | Python, Pytest, Locust, Shell | `evaluation/metrics/`, `tests/` | `feature/02-scrum-process-templates` |
| **3** | **Tech Lead & DevOps / Cloud** | Docker, GitHub Actions, Nginx | `docker-compose.yml`, `.github/workflows/`, `docs/architecture/` | `feature/03-devops-ci-cd-docker` |
| **4** | **Data Engineer 1 (Scraper & OCR)** | Python, PaddleOCR, pdfplumber | `data_pipeline/scrapers/`, `data_pipeline/ocr/` | `feature/04-data-ocr-ingestion` |
| **5** | **Data Engineer 2 (Parser & DB)** | Python, Regex, PostgreSQL, ORM | `data_pipeline/parser/`, `data_pipeline/registry/` | `feature/05-data-legal-registry` |
| **6** | **AI Engineer 1 (Hybrid Search)** | Python, BM25, pgvector, PyTorch | `ai_engine/retrieval/`, `ai_engine/reranker/` | `feature/06-ai-retrieval-search` |
| **7** | **AI Engineer 2 (Guardrails & Safety)**| Python, FastAPI, Gemini/OpenAI API| `ai_engine/guardrails/`, `ai_engine/synthesis/validator.py` | `feature/07-ai-grounding-citations` |
| **8** | **Backend Developer (API & Matter)** | Python (FastAPI), SQLAlchemy | `backend/app/api/`, `backend/app/models/`, `backend/app/services/` | `feature/08-backend-matter-services` |
| **9** | **Frontend Developer (Workspace UI)** | TypeScript, Next.js, TailwindCSS | `frontend/src/components/`, `frontend/src/pages/` | `feature/09-frontend-workspace-ui` |

---

## 🛠️ CHI TIẾT CÔNG VIỆC VÀ MÃ NGUỒN CỦA TỪNG VAI TRÒ

### 1. Thành viên 1: BA & AI Prompt Engineer (Nghiệp vụ & Kỹ sư Prompt)
* **Chuyên môn:** Phân tích yêu cầu + Kỹ thuật Prompting & Xuất báo cáo tự động.
* **Công việc cụ thể:**
  * Lập tài liệu phân tích nghiệp vụ 3 sắc thuế: GTGT (VAT), TNDN (CIT), TNCN (PIT) và Hóa đơn điện tử.
  * **Code Prompt Templates:** Lập trình các mẫu Prompt nâng cao (Few-shot, Chain-of-Thought) bắt buộc LLM chỉ trả lời dựa trên ngữ cảnh và trích dẫn cấp Điều/Khoản.
  * **Code Module Export:** Viết code Python (`python-docx`) tự động tổng hợp kết quả tra cứu và xuất ra file Word/PDF theo mẫu chuẩn doanh nghiệp có kèm link trích dẫn sống.
* **Nhánh Git:** `feature/01-po-ba-specifications`

---

### 2. Thành viên 2: Scrum Master & Automation QA Engineer (Quy trình & Kiểm thử tự động)
* **Chuyên môn:** Quản lý tiến độ Agile + Lập trình kiểm thử tự động (SDET).
* **Công việc cụ thể:**
  * Quản trị bảng Jira (Sprint, backlog, burndown chart, nhắc lịch daily họp).
  * **Code Unit Test & API Test:** Viết bộ test tự động bằng `pytest` kiểm tra toàn bộ endpoint của Backend.
  * **Code Benchmark RAG:** Viết script Python tự động tính toán các chỉ số chất lượng AI của dự án:
    * Recall@10 ≥ 90% (độ phủ tìm kiếm).
    * Citation Precision ≥ 95% (độ chuẩn xác của trích dẫn).
    * Latency p95 < 30s (đo thời gian phản hồi hệ thống).
* **Nhánh Git:** `feature/02-scrum-process-templates`

---

### 3. Thành viên 3: Tech Lead & DevOps / Cloud Engineer (Hạ tầng & Trưởng kỹ thuật)
* **Chuyên môn:** Containerization, CI/CD, Kiến trúc hệ thống & An ninh mạng.
* **Công việc cụ thể:**
  * Thiết kế kiến trúc tổng thể C4 Model (`docs/architecture/`).
  * **Code Docker:** Viết và tối ưu `docker-compose.yml`, Dockerfile cho Backend, Frontend, Postgres + pgvector.
  * **Code CI/CD:** Viết kịch bản GitHub Actions (`.github/workflows/ci.yml`) tự động linting, kiểm tra test khi tạo PR.
  * Cấu hình Reverse Proxy Nginx, quản lý biến môi trường an toàn và bảo vệ API Keys.
* **Nhánh Git:** `feature/03-devops-ci-cd-docker`

---

### 4. Thành viên 4: Data Engineer 1 (Crawl Dữ liệu & OCR Tiếng Việt)
* **Chuyên môn:** Data Ingestion, Computer Vision & Xử lý văn bản scan.
* **Công việc cụ thể:**
  * Thu thập dữ liệu các bộ luật thuế mới nhất từ Cổng thông tin Chính phủ, Công báo, Tổng cục Thuế.
  * **Code Pipeline OCR:** Viết script Python (dùng `PaddleOCR` / `pdfplumber` / `PyMuPDF`) để đọc các file PDF/ảnh scan công văn thành text sạch.
  * Xử lý giữ nguyên dấu tiếng Việt chuẩn Unicode NFC, bảo toàn cấu trúc bảng biểu và số liệu ngày tháng.
* **Nhánh Git:** `feature/04-data-ocr-ingestion`

---

### 5. Thành viên 5: Data Engineer 2 (Legal Parser & Database Schema)
* **Chuyên môn:** Xử lý chuỗi (Regex), Xử lý cấu trúc dữ liệu & Thiết kế CSDL.
* **Công việc cụ thể:**
  * Thiết kế Schema CSDL lưu trữ siêu dữ liệu văn bản pháp luật (`DAT 01`) và các đoạn trích Điều/Khoản (`DAT 02`).
  * **Code Legal Chunker:** Viết thuật toán Regex bóc tách văn bản luật tiếng Việt theo phân cấp: **Điều ➔ Khoản ➔ Điểm**.
  * Xây dựng từ điển ánh xạ viết tắt (GTGT, TNDN, TNCN, MST, HĐĐT) và phân loại cấp bậc: Luật > Nghị định > Thông tư > Công văn.
* **Nhánh Git:** `feature/05-data-legal-registry`

---

### 6. Thành viên 6: AI Engineer 1 (Search Engine & Hybrid Retrieval)
* **Chuyên môn:** Information Retrieval, Vector Search, Reranking.
* **Công việc cụ thể:**
  * **Code BM25:** Xây dựng module tìm kiếm từ khóa chính xác (khớp số hiệu nghị định, điều luật).
  * **Code Vector Search:** Tích hợp mô hình nhúng tiếng Việt (`BGE-M3` hoặc OpenAI Embeddings), lưu trữ vector vào `pgvector`.
  * **Code Hybrid Search & Reranker:** Viết thuật toán kết hợp điểm số (RRF - Reciprocal Rank Fusion) và mô hình Cross-encoder để đưa các điều luật liên quan nhất lên Top 1 - Top 3.
* **Nhánh Git:** `feature/06-ai-retrieval-search`

---

### 7. Thành viên 7: AI Engineer 2 (Safety Guardrails & Citation Validator)
* **Chuyên môn:** LLM Integration, Anti-Hallucination & An toàn dữ liệu AI.
* **Công việc cụ thể:**
  * **Code Citation Validator:** Viết thuật toán đối soát tự động kiểm tra xem điều luật do AI trích dẫn có thực sự tồn tại trong CSDL hay không.
  * **Code Abstention (Bộ từ chối):** Viết logic phát hiện câu hỏi ngoài phạm vi hoặc thiếu dữ liệu để AI yêu cầu làm rõ, không đoán mò.
  * **Code Data Redaction:** Viết module bảo mật lọc và ẩn số CCCD, Mã số thuế cá nhân, tiền lương trước khi gửi ra mô hình AI ngoài (tuân thủ Luật PDPD 91/2025).
* **Nhánh Git:** `feature/07-ai-grounding-citations`

---

### 8. Thành viên 8: Backend Developer (FastAPI & Matter Workspace)
* **Chuyên môn:** Lập trình Web API, Xử lý giao dịch & Phân quyền.
* **Công việc cụ thể:**
  * **Code RESTful API:** Xây dựng hệ thống API bằng FastAPI (Python): endpoint nhận câu hỏi `/api/v1/research`, quản lý lịch sử tra cứu.
  * **Code Matter Workspace:** Viết chức năng quản lý hồ sơ vụ việc khách hàng (tạo hồ sơ, lưu lịch sử trao đổi, cách ly dữ liệu giữa các vụ việc).
  * Viết logic phân quyền (RBAC) và Audit Log (ghi vết ai đã tra cứu, ai đã duyệt kết quả).
* **Nhánh Git:** `feature/08-backend-matter-services`

---

### 9. Thành viên 9: Frontend Developer (React / Next.js Workspace)
* **Chuyên môn:** Lập trình Web Frontend, UI/UX, Quản lý State.
* **Công việc cụ thể:**
  * **Code Giao diện Web:** Xây dựng Web App bằng Next.js + TailwindCSS.
  * Thiết kế bố cục 3 cột chuyên nghiệp:
    * Cột 1: Danh sách hồ sơ vụ việc (Matter Workspace).
    * Cột 2: Khung chat hỏi đáp AI & bộ lọc sắc thuế (VAT, CIT, PIT, năm áp dụng).
    * Cột 3: Khung trượt (Drawer) hiển thị nguyên văn đoạn trích luật gốc khi người dùng bấm vào trích dẫn.
  * Làm giao diện thẩm định cho chuyên gia (nút Phê duyệt / Từ chối / Xuất báo cáo).
* **Nhánh Git:** `feature/09-frontend-workspace-ui`
