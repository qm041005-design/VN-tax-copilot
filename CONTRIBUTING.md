# 🤝 Quy định & Hướng dẫn làm việc nhóm trên GitHub (Git Workflow)

Chào mừng 9 thành viên đến với dự án **Vietnam Tax Research Copilot (VN-tax-copilot)**!  
Tài liệu này quy định cách phối hợp mã nguồn giữa 9 thành viên để tránh xung đột code (conflict) và đồng bộ trơn tru với Jira.

---

## 👥 1. Danh sách 9 Thành viên & Phân công Nhánh làm việc

| STT | Thành viên (Họ và Tên) | GitHub Username | Vai trò đảm nhiệm | Nhánh làm việc khởi tạo |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Đặng Minh Quân (Trưởng nhóm)** | `@qm041005-design` | **BA & AI Prompt Engineer (PO)** | `feature/01-po-ba-specifications` |
| **2** | *(Thành viên chọn)* | `@...` | **Scrum Master & Automation QA** | `feature/02-scrum-process-templates` |
| **3** | *(Thành viên chọn)* | `@...` | **Tech Lead & DevOps / Cloud** | `feature/03-devops-ci-cd-docker` |
| **4** | *(Thành viên chọn)* | `@...` | **Data Engineer 1 (Crawl & OCR)** | `feature/04-data-ocr-ingestion` |
| **5** | *(Thành viên chọn)* | `@...` | **Data Engineer 2 (Parser & DB)** | `feature/05-data-legal-registry` |
| **6** | *(Thành viên chọn)* | `@...` | **AI Engineer 1 (Hybrid Search)** | `feature/06-ai-retrieval-search` |
| **7** | *(Thành viên chọn)* | `@...` | **AI Engineer 2 (Safety Guardrails)** | `feature/07-ai-grounding-citations` |
| **8** | *(Thành viên chọn)* | `@...` | **Backend Developer (FastAPI)** | `feature/08-backend-matter-services` |
| **9** | *(Thành viên chọn)* | `@...` | **Frontend Developer (Next.js)** | `feature/09-frontend-workspace-ui` |

---

## 🌳 2. Chiến lược phân nhánh (Branching Strategy)

Dự án áp dụng mô hình phân nhánh chuẩn **Git Flow**:
```text
  main (Chỉ dùng để release nghiệm thu Gate G0, G1, G2, G3, G4)
   ▲
   │ (Pull Request cuối mỗi Sprint)
  develop (Nhánh tích hợp chung của cả nhóm)
   ▲
   ├── feature/01-po-ba-specifications (Đặng Minh Quân)
   ├── feature/02-scrum-process-templates
   ├── feature/03-devops-ci-cd-docker
   ├── feature/04-data-ocr-ingestion
   ├── feature/05-data-legal-registry
   ├── feature/06-ai-retrieval-search
   ├── feature/07-ai-grounding-citations
   ├── feature/08-backend-matter-services
   └── feature/09-frontend-workspace-ui
```

* **Tuyệt đối KHÔNG commit trực tiếp vào `main` hoặc `develop`.**
* Mỗi thành viên chỉ làm việc trên nhánh `feature/...` của mình hoặc tạo nhánh con từ `develop` theo mã Jira: `feature/[MÃ-JIRA]-ten-tinh-nang` (Ví dụ: `feature/RES-01-tax-filter`).

---

## 🚀 3. Hướng dẫn từng bước cho Thành viên mới gia nhập

### Bước 1: Clone dự án về máy
```bash
git clone https://github.com/qm041005-design/VN-tax-copilot.git
cd VN-tax-copilot
```

### Bước 2: Chuyển sang nhánh tính năng được phân công
```bash
# Lấy danh sách nhánh mới nhất từ GitHub
git fetch origin

# Chuyển sang nhánh của mình (Ví dụ trưởng nhóm):
git checkout feature/01-po-ba-specifications
```

### Bước 3: Cập nhật code mới nhất từ nhánh `develop` trước khi code
```bash
git pull origin develop
```

### Bước 4: Viết code và Commit chuẩn gắn mã Jira
Quy tắc đặt tên commit:
`git commit -m "<loại>(<mã-jira>): <mô tả ngắn bằng tiếng Việt hoặc Anh>"`

* **Các loại commit:**
  * `feat`: Thêm tính năng mới (Ví dụ: `feat(RES-02): implement hybrid search BM25 and vector`)
  * `fix`: Sửa lỗi (Ví dụ: `fix(CIT-03): fix regex missing Khoan in decree citation`)
  * `docs`: Viết tài liệu (Ví dụ: `docs(PO): add acceptance criteria for VAT queries`)
  * `test`: Viết unit test hoặc benchmark dataset (Ví dụ: `test(AT-01): add 20 question fixtures`)

### Bước 5: Đẩy lên nhánh của mình và Tạo Pull Request (PR)
```bash
git push origin feature/ten-nhanh-cua-ban
```
* Lên giao diện GitHub, tạo **Pull Request** xin merge từ nhánh của bạn vào **`develop`**.
* Tag người phụ trách Review (Tech Lead hoặc bạn cặp đôi) duyệt PR trước khi merge.
