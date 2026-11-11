
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

const legalContent = {
  title: "Điều 9. Thuế suất",
  law: "Luật Thuế giá trị gia tăng",
  number: "48/2024/QH15",
  article:
    "Mức thuế suất thuế giá trị gia tăng được quy định theo từng nhóm hàng hóa, dịch vụ. Người nộp thuế cần xác định đúng đối tượng chịu thuế và mức thuế suất áp dụng theo quy định pháp luật tại thời điểm phát sinh nghĩa vụ thuế.",
  note: "Nội dung hiển thị là dữ liệu minh họa giao diện. Cần đối chiếu văn bản pháp luật gốc trước khi sử dụng tư vấn thực tế.",
};

export default function Home() {
  const [matters, setMatters] = useState(initialMatters);
  const [selectedId, setSelectedId] = useState("MT-2026-001");
  const [search, setSearch] = useState("");
  const [taxFilter, setTaxFilter] = useState("Tất cả");
  const [year, setYear] = useState("2026");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Xin chào! Tôi là VN Tax Copilot. Tôi có thể hỗ trợ bạn tra cứu quy định pháp luật thuế, phân tích tình huống và tổng hợp căn cứ pháp lý. Bạn muốn bắt đầu với vấn đề nào?",
    },
    {
      role: "assistant",
      content:
        "Đối với hồ sơ hiện tại, bạn có thể đặt câu hỏi về thuế GTGT quý III. Tôi sẽ trình bày kết quả kèm căn cứ pháp lý để bạn kiểm tra.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [reviewStatus, setReviewStatus] = useState("");
  const [notice, setNotice] = useState("");

  const selectedMatter = matters.find((item) => item.id === selectedId);

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
    setMessages([
      {
        role: "assistant",
        content: `Hồ sơ "${name.trim()}" đã được tạo. Bạn có thể bắt đầu đặt câu hỏi về thuế tại đây.`,
      },
    ]);
    setNotice("Đã tạo hồ sơ mới.");
  }

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;

    const question = draft.trim();

    setMessages((current) => [
      ...current,
      { role: "user", content: question },
      {
        role: "assistant",
        content:
          "Tôi đã tiếp nhận câu hỏi của bạn. Đây là phần phản hồi minh họa của giao diện. Khi kết nối Backend và AI Engine, nội dung sẽ được xử lý theo hồ sơ, sắc thuế và năm áp dụng đã chọn. Hãy kiểm tra căn cứ pháp lý ở khung trích dẫn bên phải.",
      },
    ]);

    setDraft("");
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
                  setMessages([
                    {
                      role: "assistant",
                      content: `Bạn đang làm việc với hồ sơ "${matter.name}". Hãy nhập câu hỏi để bắt đầu nghiên cứu.`,
                    },
                  ]);
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
                        Điều 9 - Luật Thuế GTGT 48/2024/QH15
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
              <button className="copy-button" onClick={() => {
                void navigator.clipboard?.writeText(
                  `${legalContent.title}\n${legalContent.article}`
                );
                setNotice("Đã sao chép nội dung trích dẫn.");
              }}>
                Sao chép
              </button>
            </div>

            <div className="law-card">
              <div className="law-icon">§</div>
              <div>
                <span className="law-type">VĂN BẢN PHÁP LUẬT</span>
                <h3>{legalContent.law}</h3>
                <p>Số {legalContent.number}</p>
              </div>
            </div>

            <div className="legal-content">
              <div className="article-meta">
                <span>ĐIỀU KHOẢN ĐƯỢC TRÍCH DẪN</span>
                <span className="article-number">Điều 09</span>
              </div>
              <h3>{legalContent.title}</h3>
              <p>{legalContent.article}</p>

              <div className="highlight-note">
                <div className="note-heading">
                  <span>i</span> Lưu ý pháp lý
                </div>
                {legalContent.note}
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
                <strong>{legalContent.number}</strong>
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
