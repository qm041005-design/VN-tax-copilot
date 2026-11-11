
"use client";

import { useMemo, useState, type FormEvent } from "react";

type Matter = {
  id: string;
  name: string;
  company: string;
  tax: string;
  updated: string;
  status: "Đang xử lý" | "Chờ duyệt" | "Đã duyệt";
};

type Message = {
  role: "assistant" | "user";
  content: string;
};

const initialMatters: Matter[] = [
  {
    id: "MT-2026-001",
    name: "Rà soát thuế GTGT quý III",
    company: "Công ty TNHH Minh Phát",
    tax: "VAT",
    updated: "10 phút trước",
    status: "Đang xử lý",
  },
  {
    id: "MT-2026-002",
    name: "Quyết toán thuế TNDN 2025",
    company: "Công ty CP An Khang",
    tax: "CIT",
    updated: "Hôm qua",
    status: "Chờ duyệt",
  },
  {
    id: "MT-2026-003",
    name: "Kiểm tra thuế TNCN",
    company: "Công ty TNHH Hoàng Gia",
    tax: "PIT",
    updated: "2 ngày trước",
    status: "Đã duyệt",
  },
];

type LegalContent = {
  title: string;
  articleNo: string;
  law: string;
  shortLaw: string;
  number: string;
  article: string;
  note: string;
};

const legalNote =
  "Nội dung hiển thị là dữ liệu minh họa giao diện. Cần đối chiếu văn bản pháp luật gốc trước khi sử dụng tư vấn thực tế.";

const legalByTax: Record<string, LegalContent> = {
  VAT: {
    title: "Điều 9. Thuế suất",
    articleNo: "Điều 09",
    law: "Luật Thuế giá trị gia tăng",
    shortLaw: "Luật Thuế GTGT",
    number: "48/2024/QH15",
    article:
      "Mức thuế suất thuế giá trị gia tăng được quy định theo từng nhóm hàng hóa, dịch vụ. Người nộp thuế cần xác định đúng đối tượng chịu thuế và mức thuế suất áp dụng theo quy định pháp luật tại thời điểm phát sinh nghĩa vụ thuế.",
    note: legalNote,
  },
  CIT: {
    title: "Điều 10. Thuế suất",
    articleNo: "Điều 10",
    law: "Luật Thuế thu nhập doanh nghiệp",
    shortLaw: "Luật Thuế TNDN",
    number: "67/2025/QH15",
    article:
      "Thuế suất thuế thu nhập doanh nghiệp được xác định theo quy mô doanh thu và loại hình hoạt động của doanh nghiệp. Người nộp thuế cần xác định đúng mức thuế suất áp dụng cho kỳ tính thuế và các trường hợp được áp dụng mức thuế suất khác.",
    note: legalNote,
  },
  PIT: {
    title: "Điều 9. Biểu thuế lũy tiến từng phần",
    articleNo: "Điều 09",
    law: "Luật Thuế thu nhập cá nhân",
    shortLaw: "Luật Thuế TNCN",
    number: "109/2025/QH15",
    article:
      "Thu nhập tính thuế từ tiền lương, tiền công của cá nhân cư trú được áp dụng biểu thuế lũy tiến từng phần. Người nộp thuế cần xác định đúng thu nhập tính thuế và bậc thuế áp dụng theo quy định tại thời điểm tính thuế.",
    note: legalNote,
  },
};

function getLegalContent(tax: string | undefined): LegalContent {
  return legalByTax[tax ?? "VAT"] ?? legalByTax.VAT;
}

const introMessage: Message = {
  role: "assistant",
  content:
    "Xin chào! Tôi là VN Tax Copilot. Tôi có thể hỗ trợ bạn tra cứu quy định pháp luật thuế, phân tích tình huống và tổng hợp căn cứ pháp lý. Bạn muốn bắt đầu với vấn đề nào?",
};

function welcomeMessages(matter: Matter | undefined): Message[] {
  if (!matter) return [introMessage];
  return [
    introMessage,
    {
      role: "assistant",
      content: `Đối với hồ sơ "${matter.name}", bạn có thể đặt câu hỏi liên quan. Tôi sẽ trình bày kết quả kèm căn cứ pháp lý để bạn kiểm tra.`,
    },
  ];
}

export default function Home() {
  const [matters, setMatters] = useState(initialMatters);
  const [selectedId, setSelectedId] = useState("MT-2026-001");
  const [search, setSearch] = useState("");
  const [taxFilter, setTaxFilter] = useState("Tất cả");
  const [year, setYear] = useState("2026");
  // Lịch sử chat và câu đang nhập được lưu riêng cho từng hồ sơ.
  const [conversations, setConversations] = useState<
    Record<string, Message[]>
  >({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [reviewStatus, setReviewStatus] = useState("");
  const [notice, setNotice] = useState("");

  const selectedMatter = matters.find((item) => item.id === selectedId);
  const messages = conversations[selectedId] ?? welcomeMessages(selectedMatter);
  const draft = drafts[selectedId] ?? "";
  const legal = getLegalContent(selectedMatter?.tax);

  function setDraft(value: string) {
    setDrafts((current) => ({ ...current, [selectedId]: value }));
  }

  const filteredMatters = useMemo(() => {
    return matters.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.company.toLowerCase().includes(search.toLowerCase());

      const matchesTax =
        taxFilter === "Tất cả" || item.tax === taxFilter;

      return matchesSearch && matchesTax;
    });
  }, [matters, search, taxFilter]);

  function createMatter() {
    const name = window.prompt("Nhập tên hồ sơ vụ việc:");
    if (!name?.trim()) return;

    const newMatter: Matter = {
      id: `MT-2026-${String(matters.length + 1).padStart(3, "0")}`,
      name: name.trim(),
      company: "Khách hàng mới",
      tax: "VAT",
      updated: "Vừa tạo",
      status: "Đang xử lý",
    };

    setMatters((current) => [newMatter, ...current]);
    setSelectedId(newMatter.id);
    setReviewStatus("");
    setConversations((current) => ({
      ...current,
      [newMatter.id]: [
        {
          role: "assistant",
          content: `Hồ sơ "${name.trim()}" đã được tạo. Bạn có thể bắt đầu đặt câu hỏi về thuế tại đây.`,
        },
      ],
    }));
    setNotice("Đã tạo hồ sơ mới.");
  }

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;

    const question = draft.trim();
    const matterId = selectedId;
    const baseMessages = messages;

    setConversations((current) => ({
      ...current,
      [matterId]: [
        ...(current[matterId] ?? baseMessages),
        { role: "user", content: question },
        {
          role: "assistant",
          content:
            "Tôi đã tiếp nhận câu hỏi của bạn. Đây là phần phản hồi minh họa của giao diện. Khi kết nối Backend và AI Engine, nội dung sẽ được xử lý theo hồ sơ, sắc thuế và năm áp dụng đã chọn. Hãy kiểm tra căn cứ pháp lý ở khung trích dẫn bên phải.",
        },
      ],
    }));
    setDrafts((current) => ({ ...current, [matterId]: "" }));
  }

  function updateReview(status: "Đã duyệt" | "Từ chối") {
    if (!selectedMatter) return;

    if (status === "Từ chối") {
      const reason = window.prompt("Nhập lý do từ chối:");
      if (!reason?.trim()) return;
    }

    if (status === "Đã duyệt") {
      setMatters((current) =>
        current.map((item) =>
          item.id === selectedId ? { ...item, status } : item
        )
      );
    }

    setReviewStatus(status);
    setNotice(
      status === "Đã duyệt"
        ? "Hồ sơ đã được đánh dấu phê duyệt."
        : "Đã ghi nhận thao tác từ chối (minh họa)."
    );
  }

  async function copyCitation() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(`${legal.title}\n${legal.article}`);
      setNotice("Đã sao chép nội dung trích dẫn.");
    } catch {
      setNotice("Không thể sao chép. Vui lòng sao chép thủ công.");
    }
  }

  function exportReport() {
    const report = [
      "VN TAX COPILOT - BAO CAO HO SO",
      `Ma ho so: ${selectedMatter?.id ?? ""}`,
      `Ten ho so: ${selectedMatter?.name ?? ""}`,
      `Khach hang: ${selectedMatter?.company ?? ""}`,
      `Sac thue: ${selectedMatter?.tax ?? ""}`,
      `Nam ap dung: ${year}`,
      "",
      "LICH SU TRAO DOI",
      ...messages.map(
        (message) =>
          `${message.role === "user" ? "Nguoi dung" : "AI"}: ${message.content}`
      ),
      "",
      "Bao cao minh hoa - can doi chieu truoc khi su dung.",
    ].join("\n");

    const blob = new Blob([report], {
      type: "text/plain;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bao-cao-${selectedMatter?.id ?? "ho-so"}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    setNotice("Đã xuất báo cáo mẫu.");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">V</div>
          <div>
            <div className="brand-name">VN TAX COPILOT</div>
            <div className="brand-subtitle">Tax Research Workspace</div>
          </div>
        </div>

        <div className="topbar-center">
          <span className="workspace-label">WORKSPACE</span>
          <span className="topbar-divider">/</span>
          <span className="topbar-current">Nghiên cứu thuế</span>
        </div>

        <div className="topbar-actions">
          <span className="system-status">
            <span className="status-dot" />
            Hệ thống hoạt động
          </span>
          <div className="avatar">P</div>
          <div className="user-info">
            <strong>Phước</strong>
            <span>Chuyên viên thuế</span>
          </div>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="sidebar">
          <div className="sidebar-heading">
            <div>
              <span className="eyebrow">WORKSPACE</span>
              <h2>Hồ sơ vụ việc</h2>
            </div>
            <button
              className="icon-button create-button"
              onClick={createMatter}
              title="Tạo hồ sơ mới"
            >
              +
            </button>
          </div>

          <button className="new-matter-button" onClick={createMatter}>
            <span>＋</span> Tạo hồ sơ mới
          </button>

          <div className="search-box">
            <span>⌕</span>
            <input
              aria-label="Tìm hồ sơ hoặc khách hàng"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Tìm hồ sơ, khách hàng..."
            />
          </div>

          <div className="sidebar-section-title">
            DANH SÁCH HỒ SƠ
            <span>{filteredMatters.length}</span>
          </div>

          <div className="matter-list">
            {filteredMatters.map((matter) => (
              <button
                key={matter.id}
                className={`matter-card ${
                  selectedId === matter.id ? "selected" : ""
                }`}
                onClick={() => {
                  setSelectedId(matter.id);
                  setReviewStatus("");
                }}
              >
                <div className="matter-card-top">
                  <span className={`tax-tag ${matter.tax.toLowerCase()}`}>
                    {matter.tax}
                  </span>
                  <span className="matter-time">{matter.updated}</span>
                </div>
                <strong className="matter-name">{matter.name}</strong>
                <span className="matter-company">{matter.company}</span>
                <div className="matter-card-bottom">
                  <span className="matter-id">{matter.id}</span>
                  <span
                    className={`matter-status ${
                      matter.status === "Đã duyệt"
                        ? "approved"
                        : matter.status === "Chờ duyệt"
                          ? "pending"
                          : ""
                    }`}
                  >
                    {matter.status}
                  </span>
                </div>
              </button>
            ))}

            {filteredMatters.length === 0 && (
              <div className="empty-state">
                Không tìm thấy hồ sơ phù hợp.
              </div>
            )}
          </div>

          <div className="sidebar-bottom">
            <div className="storage-card">
              <div className="storage-icon">▤</div>
              <div>
                <strong>Kho dữ liệu pháp luật</strong>
                <span>Tra cứu văn bản và điều khoản</span>
              </div>
              <span className="arrow">→</span>
            </div>
            <div className="sidebar-footer">
              VN Tax Copilot <span>v1.0.0</span>
            </div>
          </div>
        </aside>

        <section className="chat-workspace">
          <div className="page-heading">
            <div>
              <div className="breadcrumb">
                Hồ sơ <span>/</span> {selectedMatter?.id ?? "Chưa chọn"}
              </div>
              <h1>{selectedMatter?.name ?? "Chưa chọn hồ sơ"}</h1>
              <p>
                {selectedMatter?.company ?? "Chọn một hồ sơ để bắt đầu"}
                <span className="heading-separator">·</span>
                Nghiên cứu và tư vấn pháp luật thuế
              </p>
            </div>
            <button
              className="outline-button"
              onClick={() => setDrawerOpen((value) => !value)}
            >
              {drawerOpen ? "Ẩn trích dẫn" : "Hiện trích dẫn"}
            </button>
          </div>

          <div className="filter-panel">
            <div className="filter-group">
              <label>SẮC THUẾ</label>
              <div className="filter-options">
                {["Tất cả", "VAT", "CIT", "PIT"].map((tax) => (
                  <button
                    key={tax}
                    className={taxFilter === tax ? "active" : ""}
                    onClick={() => setTaxFilter(tax)}
                  >
                    {tax}
                  </button>
                ))}
              </div>
            </div>
            <div className="filter-divider" />
            <div className="year-filter">
              <label htmlFor="tax-year">NĂM ÁP DỤNG</label>
              <select
                id="tax-year"
                value={year}
                onChange={(event) => setYear(event.target.value)}
              >
                <option value="2024">2024</option>
                <option value="2025">2025</option>
                <option value="2026">2026</option>
              </select>
            </div>
            <div className="filter-context">
              <span className="context-dot" />
              Đang lọc dữ liệu
            </div>
          </div>

          <div className="conversation-area">
            <div className="conversation-date">
              <span />
              PHIÊN TRA CỨU HIỆN TẠI
              <span />
            </div>

            <div className="ai-intro">
              <div className="ai-avatar">AI</div>
              <div className="message-content">
                <div className="message-author">
                  VN Tax Copilot <span>Trợ lý AI</span>
                </div>
                <div className="message-bubble">
                  {messages[0]?.content}
                </div>
              </div>
            </div>

            {messages.slice(1).map((message, index) => (
              <div
                key={index}
                className={`message-row ${
                  message.role === "user" ? "user-message" : "ai-message"
                }`}
              >
                {message.role === "assistant" && (
                  <div className="ai-avatar small">AI</div>
                )}
                <div className="message-content">
                  {message.role === "assistant" && (
                    <div className="message-author">
                      VN Tax Copilot <span>Trợ lý AI</span>
                    </div>
                  )}
                  <div className="message-bubble">{message.content}</div>
                  {message.role === "assistant" && (
                    <div className="citation-preview">
                      <div className="citation-label">
                        <span>▤</span> CĂN CỨ PHÁP LÝ
                      </div>
                      <button
                        className="citation-link"
                        onClick={() => setDrawerOpen(true)}
                      >
                        {legal.title.split(".")[0]} - {legal.shortLaw}{" "}
                        {legal.number}
                        <span>↗</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="chat-bottom">
            <div className="suggestion-row">
              <button
                onClick={() =>
                  setDraft("Điều kiện khấu trừ thuế GTGT đầu vào là gì?")
                }
              >
                Điều kiện khấu trừ thuế GTGT?
              </button>
              <button
                onClick={() =>
                  setDraft("Các quy định thuế mới áp dụng năm 2026?")
                }
              >
                Quy định thuế mới 2026?
              </button>
            </div>

            <form className="chat-input-area" onSubmit={sendMessage}>
              <textarea
                aria-label="Nhập câu hỏi về thuế"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Nhập câu hỏi về thuế hoặc yêu cầu tra cứu văn bản pháp luật..."
                rows={2}
              />
              <div className="input-toolbar">
                <span>AI có thể đưa ra thông tin chưa chính xác. Hãy kiểm tra căn cứ pháp lý.</span>
                <button type="submit" disabled={!draft.trim()}>
                  Gửi câu hỏi <span>↑</span>
                </button>
              </div>
            </form>
          </div>
        </section>

        {drawerOpen && (
          <aside className="legal-panel">
            <div className="legal-header">
              <div>
                <span className="eyebrow">LEGAL REFERENCE</span>
                <h2>Trích dẫn pháp lý</h2>
              </div>
              <button
                className="icon-button close-button"
                onClick={() => setDrawerOpen(false)}
                title="Đóng bảng trích dẫn"
              >
                ×
              </button>
            </div>

            <div className="legal-toolbar">
              <span className="verified-tag">
                <span /> VĂN BẢN THAM CHIẾU
              </span>
              <button className="copy-button" onClick={copyCitation}>
                Sao chép
              </button>
            </div>

            <div className="law-card">
              <div className="law-icon">§</div>
              <div>
                <span className="law-type">VĂN BẢN PHÁP LUẬT</span>
                <h3>{legal.law}</h3>
                <p>Số {legal.number}</p>
              </div>
            </div>

            <div className="legal-content">
              <div className="article-meta">
                <span>ĐIỀU KHOẢN ĐƯỢC TRÍCH DẪN</span>
                <span className="article-number">{legal.articleNo}</span>
              </div>
              <h3>{legal.title}</h3>
              <p>{legal.article}</p>

              <div className="highlight-note">
                <div className="note-heading">
                  <span>i</span> Lưu ý pháp lý
                </div>
                {legal.note}
              </div>
            </div>

            <div className="source-details">
              <div className="source-heading">THÔNG TIN NGUỒN</div>
              <div className="source-row">
                <span>Loại văn bản</span>
                <strong>Luật</strong>
              </div>
              <div className="source-row">
                <span>Số hiệu</span>
                <strong>{legal.number}</strong>
              </div>
              <div className="source-row">
                <span>Năm áp dụng</span>
                <strong>{year}</strong>
              </div>
              <div className="source-row">
                <span>Sắc thuế</span>
                <strong>{selectedMatter?.tax ?? "VAT"}</strong>
              </div>
            </div>

            <div className="legal-footer">
              <span>VN Tax Copilot · Legal Research</span>
              <span>↗</span>
            </div>
          </aside>
        )}
      </div>

      <footer className="review-bar">
        <div className="review-info">
          <span className="review-indicator" />
          <div>
            <strong>Thẩm định kết quả</strong>
            <span>
              {reviewStatus
                ? `Trạng thái thao tác: ${reviewStatus}`
                : "Vui lòng kiểm tra nội dung trước khi phê duyệt"}
            </span>
          </div>
        </div>

        {notice && <span className="notice-message">{notice}</span>}

        <div className="review-actions">
          <button
            className="reject-button"
            onClick={() => updateReview("Từ chối")}
          >
            Từ chối
          </button>
          <button
            className="approve-button"
            onClick={() => updateReview("Đã duyệt")}
          >
            ✓ Phê duyệt
          </button>
          <button className="export-button" onClick={exportReport}>
            ↓ Xuất báo cáo
          </button>
        </div>
      </footer>
    </main>
  );
}
