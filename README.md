# 🇻🇳 Vietnam Tax Research Copilot with Citations (VN-tax-copilot)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Framework: Scrum](https://img.shields.io/badge/Methodology-Scrum%20(8%20Sprints)-orange.svg)](https://scrumguides.org/)
[![Focus: Legal RAG](https://img.shields.io/badge/Core-Legal%20RAG%20%7C%20Citation%20Pinpoint-brightgreen.svg)](#)
[![Compliance: Vietnam PDPD](https://img.shields.io/badge/Compliance-PDPD%20%26%20AI%20Law-red.svg)](#)

> **Enterprise Semester Capstone Project (Học kỳ doanh nghiệp)**  
> **Customer / RFP Benchmark:** THTax ([thtax.vn](https://thtax.vn))  
> **Project Repository:** [qm041005-design/VN-tax-copilot](https://github.com/qm041005-design/VN-tax-copilot)

---

## 📌 1. Giới thiệu tổng quan (Overview)

**VN-tax-copilot** là hệ thống trợ lý ảo AI chuyên biệt phục vụ công tác nghiên cứu, tra cứu và thẩm định pháp luật Thuế tại Việt Nam dành cho các chuyên viên thuế, kế toán và kiểm toán viên. Hệ thống tập trung vào 3 sắc thuế trọng điểm:
* **Thuế Giá trị gia tăng (GTGT / VAT)**
* **Thuế Thu nhập doanh nghiệp (TNDN / CIT)**
* **Thuế Thu nhập cá nhân (TNCN / PIT)**
* *(Kèm quy định về Quản lý thuế & Hóa đơn điện tử liên quan)*

### 🎯 4 Trụ cột cốt lõi (Core Pillars)
1. **Trích dẫn chính xác cấp Điều - Khoản - Điểm (Pinpoint Citations):** Không sinh câu trả lời cảm tính (Zero Hallucination). Mọi kết luận pháp lý đều được ánh xạ với nguồn gốc rõ ràng và trích đoạn nguyên văn.
2. **Thứ bậc hiệu lực pháp lý (Legal Hierarchy):** Nhận biết và phân cấp rõ ràng giữa *Luật / Nghị quyết > Nghị định > Thông tư > Công văn hành chính*. Không bao giờ coi Công văn hướng dẫn cá biệt là văn bản quy phạm pháp luật chung.
3. **Hiệu lực theo thời gian (Temporal Applicability):** Cho phép tra cứu chính xác theo từng kỳ tính thuế (năm/tháng áp dụng luật cũ, luật sửa đổi bổ sung hay quy định chuyển tiếp).
4. **Không gian làm việc & Chuyên gia thẩm định (Matter Workspace & Human Review):** Lưu trữ theo từng hồ sơ vụ việc khách hàng, hỗ trợ workflow thẩm định (*Draft ➔ In Review ➔ Approved/Rejected*) và xuất báo cáo DOCX/PDF kèm danh mục trích dẫn sống.

---

## 👥 2. Cơ cấu nhóm & Phân vai (Team Structure - 9 Members)

Dự án vận hành theo mô hình **Scrum Agile (8 Sprints - 16 tuần)** với 9 thành viên:

| STT | Thành viên / Role | Trách nhiệm chính trong dự án | Trọng tâm trên Jira / Backlog |
| :---: | :--- | :--- | :--- |
| **1** | **Product Owner (PO) & BA** | Định hình Product Backlog, làm rõ nghiệp vụ thuế (GTGT, TNDN, TNCN), viết User Story & AC (Gherkin), quản lý tiêu chí nghiệm thu G0-G4. | Quản lý Release Gates & User Stories |
| **2** | **Scrum Master (SM) & Fullstack** | Điều phối Scrum ceremonies (Daily, Planning, Review, Retro), gỡ bỏ chướng ngại vật (impediments), hỗ trợ tích hợp code. | Sprint Board, Burndown & Velocity |
| **3** | **Tech Lead & DevOps / Cloud** | Thiết kế kiến trúc tổng thể, CI/CD pipeline, Dockerization, bảo mật (RBAC, SSO), logging, giám sát chi phí token & độ trễ. | `[EPIC-06] Architecture & Security` |
| **4** | **Data Engineer 1 (Ingestion & OCR)** | Thu thập dữ liệu pháp điển, OCR tiếng Việt chất lượng cao (bảo toàn bảng biểu, cấu trúc), xử lý file scan. | `[EPIC-01] Data Ingestion & OCR` |
| **5** | **Data Engineer 2 (Legal Registry)** | Quản lý siêu dữ liệu (Metadata), trạng thái hiệu lực (còn hiệu lực, hết hiệu lực, sửa đổi), quan hệ các văn bản quy phạm. | `[EPIC-02] Legal Versioning & Registry` |
| **6** | **AI / RAG Engineer 1 (Retrieval)** | Xây dựng Hybrid Search (BM25 + Dense Vector), Reranker (Cross-encoder), Metadata Filter theo năm/thẩm quyền (Recall@10 ≥ 90%). | `[EPIC-03] Hybrid Retrieval & Search` |
| **7** | **AI / RAG Engineer 2 (Generation & Safety)**| Prompt Engineering, Grounded Synthesis, Citation Validator (kiểm tra claim vs passage), bộ từ chối trả lời khi thiếu dữ liệu (Abstention). | `[EPIC-04] Grounded AI & Validation` |
| **8** | **Backend Engineer** | RESTful APIs, quản lý User/Matter Workspace, phân quyền dữ liệu, Audit Log, Module xuất báo cáo DOCX/PDF. | `[EPIC-05] Backend & Matter Services` |
| **9** | **Frontend Engineer (UI/UX)** | Xây dựng Web App (Next.js/React), Chat Workspace, Citation Drawer/Preview, Review & Approval dashboard (chuẩn WCAG AA). | `[EPIC-05] Frontend & Workspace UI` |

---

## 🏗️ 3. Cấu trúc thư mục Monorepo (Project Structure)

```text
VN-tax-copilot/
├── frontend/                   # Web Application (Next.js / React / TailwindCSS)
│   ├── src/
│   │   ├── components/         # ChatBox, CitationDrawer, MatterWorkspace, ReviewPanel
│   │   ├── pages/ (or app/)    # Routes: /research, /matters, /admin, /review
│   │   └── services/           # API Client
├── backend/                    # Core Backend Services (FastAPI / Python)
│   ├── app/
│   │   ├── api/                # Router endpoints (v1): /search, /matters, /export
│   │   ├── core/               # Config, Security, Auth, RBAC, Database session
│   │   ├── models/             # SQLAlchemy / ORM models (Matter, AuditLog, User)
│   │   └── services/           # MatterService, ExportService (DOCX/PDF generation)
├── ai_engine/                  # RAG & LLM Pipeline
│   ├── retrieval/              # Hybrid Search (BM25 + Vector DB Qdrant/Pgvector)
│   ├── reranker/               # Cross-encoder Reranker models
│   ├── synthesis/              # LLM Chains, Grounding Prompts, Structured Output
│   └── guardrails/             # Citation Validator, Redaction (PDPD), Abstention logic
├── data_pipeline/              # Ingestion, OCR & Legal Registry
│   ├── scrapers/               # Crawlers từ Cổng thông tin Chính phủ, Công báo, TCT
│   ├── ocr/                    # Vietnamese OCR Engine & Page mapping
│   ├── parser/                 # Legal Chunking Engine (Điều - Khoản - Điểm)
│   └── registry/               # Metadata schema & Versioning tracker
├── evaluation/                 # Benchmark & Acceptance Test Suite
│   ├── datasets/               # 200 answerable questions + 50 ambiguous cases
│   ├── vietnam_suite/          # 60 test cases đặc thù (VN 06)
│   └── metrics/                # Scripts đo lường Recall@10, Citation Validity, Latency
├── docs/                       # Tài liệu thiết kế & Báo cáo
│   ├── architecture/           # Sơ đồ C4, sequence diagrams
│   ├── jira_wbs/               # Danh sách Epics, User Stories, Sprint Backlog
│   └── rfp/                    # Tài liệu RFP THTax & Traceability Matrix
├── docker-compose.yml          # Setup local development environment
└── README.md
```

---

## 📅 4. Lộ trình phát triển 8 Sprints (16 Weeks WBS)

* **Sprint 1 (Tuần 1 - 2 | Gate G0):** Project Kickoff, Jira setup, Schema Database, Pháp điển hóa nguồn tài liệu mẫu.
* **Sprint 2 (Tuần 3 - 4 | Gate G1):** Pipeline OCR tiếng Việt, Chunking theo Điều/Khoản/Điểm, Search Baseline (BM25).
* **Sprint 3 (Tuần 5 - 6):** Vector Embeddings, Hybrid Search + Reranker, Giao diện Chat Copilot ban đầu.
* **Sprint 4 (Tuần 7 - 8 | Gate G2):** Grounded AI Synthesis, Citation Preview Drawer, Tích hợp Matter Workspace.
* **Sprint 5 (Tuần 9 - 10):** Bộ xác thực trích dẫn (Citation Validator), Redaction bảo mật dữ liệu nhạy cảm (PDPD).
* **Sprint 6 (Tuần 11 - 12):** Load testing (10-50 concurrent users), Xuất báo cáo DOCX/PDF, Kiểm thử bảo mật (Prompt Injection).
* **Sprint 7 (Tuần 13 - 14 | Gate G3):** Chạy nghiệm thu 200 câu hỏi benchmark + 60 kịch bản thuế Việt Nam (`VN 06`).
* **Sprint 8 (Tuần 15 - 16 | Gate G4):** Hoàn thiện bàn giao, đóng gói Docker/Runbook, bảo vệ đồ án trước hội đồng.

---

## ⚖️ 5. Tuân thủ pháp lý & Bảo mật (Compliance)
Dự án được thiết kế đáp ứng các tiêu chuẩn pháp lý tại Việt Nam:
* **Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 & Nghị định 356/2025/NĐ-CP:** Tự động che giấu (redact) mã số thuế cá nhân, số CCCD, bảng lương trước khi gửi prompt tới LLM.
* **Luật Trí tuệ nhân tạo 134/2025/QH15:** Minh bạch xuất xứ câu trả lời, gắn nhãn rõ ràng bản dự thảo do AI tạo lập và luôn yêu cầu chuyên gia con người thẩm định cuối cùng.
* **Luật An ninh mạng 116/2025/QH15 & Quy tắc OWASP Top 10 for LLM Applications.**
