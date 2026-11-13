"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  api,
  type Citation,
  type HistoryItem,
  type Matter as ApiMatter,
  type SourceDetail,
  type SourceHit,
  type TaxType,
} from "@/services/api";

type Matter = {
  id: string;
  name: string;
  company: string;
  tax: string;
  updated: string;
  status: "Đang xử lý" | "Lưu trữ";
};

function fromApiMatter(item: ApiMatter): Matter {
  return {
    id: item.id,
    name: item.title,
    company: item.client_name,
    tax: item.tax_types[0] ?? "VAT",
    updated: new Date(item.updated_at).toLocaleDateString("vi-VN"),
    status: item.status === "archived" ? "Lưu trữ" : "Đang xử lý",
  };
}

function getError(error: unknown): string {
  return error instanceof Error ? error.message : "Có lỗi khi kết nối API.";
}

function citationLabel(item: Citation): string {
  const parts = [
    item.diem ? `Điểm ${item.diem}` : null,
    item.khoan ? `Khoản ${item.khoan}` : null,
    item.dieu ? `Điều ${item.dieu}` : null,
    item.legal_identifier,
  ].filter(Boolean);
  return parts.join(", ") || item.title || `Nguồn #${item.source_id}`;
}

function byCreatedAt(a: HistoryItem, b: HistoryItem): number {
  return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
}

function reviewLabel(status: string | undefined): string {
  switch (status) {
    case "draft": return "Bản nháp — chưa thẩm định";
    case "under_review": return "Đang thẩm định";
    case "approved": return "Đã duyệt trên backend";
    case "rejected": return "Bị từ chối trên backend";
    case "superseded": return "Đã thay thế";
    default: return "Chưa có kết quả tra cứu";
  }
}

export default function Home() {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const selectedIdRef = useRef("");
  selectedIdRef.current = selectedId;

  const [loadingMatters, setLoadingMatters] = useState(true);
  const [creatingMatter, setCreatingMatter] = useState(false);
  const [mattersError, setMattersError] = useState("");
  const [search, setSearch] = useState("");
  const [taxFilter, setTaxFilter] = useState("Tất cả");
  const [year, setYear] = useState("2026");

  // Dữ liệu lịch sử được lưu ở backend và tách riêng cho từng hồ sơ.
  const [histories, setHistories] = useState<Record<string, HistoryItem[]>>({});
  const [historyLoadingId, setHistoryLoadingId] = useState<string | null>(null);
  const [historyErrors, setHistoryErrors] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [sendErrors, setSendErrors] = useState<Record<string, string>>({});
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [notice, setNotice] = useState("");

  // Tìm kiếm nguồn luật thật, không lấy dữ liệu luật từ hằng số giả.
  const [sourceQuery, setSourceQuery] = useState("");
  const [sourceHits, setSourceHits] = useState<SourceHit[]>([]);
  const [sourceSearchDone, setSourceSearchDone] = useState(false);
  const [sourceSearchLoading, setSourceSearchLoading] = useState(false);
  const [sourceSearchError, setSourceSearchError] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState("");

  useEffect(() => {
    let active = true;
    api.getMatters()
      .then((data) => {
        if (!active) return;
        setMatters(data.items.map(fromApiMatter));
        setSelectedId((current) => current || data.items[0]?.id || "");
        setMattersError("");
      })
      .catch((error: unknown) => {
        if (active) setMattersError(getError(error));
      })
      .finally(() => { if (active) setLoadingMatters(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    const id = selectedId;
    setHistoryLoadingId(id);
    setHistoryErrors((current) => ({ ...current, [id]: "" }));
    api.getHistory(id)
      .then((items) => {
        if (!active) return;
        setHistories((current) => {
          // Giữ những lượt tra cứu mới gửi trong khi GET lịch sử còn đang tải.
          const merged = new Map<string, HistoryItem>();
          for (const item of items) merged.set(item.id, item);
          for (const item of current[id] ?? []) merged.set(item.id, item);
          return { ...current, [id]: Array.from(merged.values()).sort(byCreatedAt) };
        });
      })
      .catch((error: unknown) => {
        if (active) setHistoryErrors((current) => ({ ...current, [id]: getError(error) }));
      })
      .finally(() => {
        if (active) setHistoryLoadingId((current) => current === id ? null : current);
      });
    return () => { active = false; };
  }, [selectedId]);

  useEffect(() => {
    // Không để nguồn luật từ hồ sơ A xuất hiện khi đang chọn hồ sơ B.
    setSourceHits([]);
    setSourceQuery("");
    setSourceSearchDone(false);
    setSourceSearchError("");
    setSelectedCitation(null);
    setSourceDetail(null);
    setSourceError("");
  }, [selectedId]);

  useEffect(() => {
    let active = true;
    setSourceDetail(null);
    setSourceError("");
    if (!selectedCitation) {
      setSourceLoading(false);
      return () => { active = false; };
    }
    setSourceLoading(true);
    api.getSource(selectedCitation.source_id)
      .then((data) => { if (active) setSourceDetail(data); })
      .catch((error: unknown) => { if (active) setSourceError(getError(error)); })
      .finally(() => { if (active) setSourceLoading(false); });
    return () => { active = false; };
  }, [selectedCitation]);

  const selectedMatter = matters.find((item) => item.id === selectedId);
  const history = histories[selectedId] ?? [];
  const latestHistory = history[history.length - 1];
  const draft = drafts[selectedId] ?? "";
  const filteredMatters = useMemo(() => matters.filter((item) => {
    const lower = search.toLowerCase();
    return (item.name.toLowerCase().includes(lower) || item.company.toLowerCase().includes(lower)) &&
      (taxFilter === "Tất cả" || item.tax === taxFilter);
  }), [matters, search, taxFilter]);

  function setDraft(value: string) {
    if (!selectedId) return;
    setDrafts((current) => ({ ...current, [selectedId]: value }));
  }

  async function createMatter() {
    if (creatingMatter) return;
    const title = window.prompt("Nhập tên hồ sơ:");
    if (!title?.trim()) return;
    const clientName = window.prompt("Nhập tên khách hàng:");
    if (!clientName?.trim()) return;

    try {
      setCreatingMatter(true);
      setMattersError("");
      const tax: TaxType = taxFilter === "VAT" || taxFilter === "CIT" || taxFilter === "PIT"
        ? taxFilter : "VAT";
      const created = await api.createMatter({
        title: title.trim(), client_name: clientName.trim(),
        tax_types: [tax], tax_period: year,
      });
      setMatters((current) => [fromApiMatter(created), ...current]);
      setSearch("");
      setTaxFilter("Tất cả");
      setSelectedId(created.id);
      setNotice("Đã tạo hồ sơ và lưu vào PostgreSQL.");
    } catch (error) {
      setMattersError(getError(error));
    } finally {
      setCreatingMatter(false);
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !draft.trim() || sendingId !== null) return;
    const matterId = selectedId;
    const question = draft.trim();
    if (question.length > 2000) {
      setSendErrors((current) => ({ ...current, [matterId]: "Câu hỏi tối đa 2000 ký tự." }));
      return;
    }

    try {
      setSendingId(matterId);
      setSendErrors((current) => ({ ...current, [matterId]: "" }));
      const tax: TaxType | undefined =
        taxFilter === "VAT" || taxFilter === "CIT" || taxFilter === "PIT"
          ? taxFilter : selectedMatter?.tax === "VAT" || selectedMatter?.tax === "CIT" || selectedMatter?.tax === "PIT"
            ? selectedMatter.tax : undefined;
      const result = await api.research({
        matter_id: matterId,
        question,
        ...(tax ? { tax_type: tax } : {}),
        tax_period: year,
      });
      setHistories((current) => {
        const merged = new Map((current[matterId] ?? []).map((item) => [item.id, item]));
        merged.set(result.history.id, result.history);
        return { ...current, [matterId]: Array.from(merged.values()).sort(byCreatedAt) };
      });
      setDrafts((current) => ({ ...current, [matterId]: "" }));
      if (selectedIdRef.current === matterId) {
        setSourceHits(result.sources);
        setSourceSearchDone(true);
        setSourceSearchError("");
        setSelectedCitation(result.sources[0] ?? result.history.citations[0] ?? null);
      }
      setNotice("Đã lưu lượt tra cứu vào hồ sơ. Kết quả đang ở trạng thái bản nháp.");
    } catch (error) {
      setSendErrors((current) => ({ ...current, [matterId]: getError(error) }));
    } finally {
      setSendingId(null);
    }
  }

  async function searchLegalSources(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = sourceQuery.trim();
    if (!query || sourceSearchLoading) return;
    const matterId = selectedId;
    try {
      setSourceSearchLoading(true);
      setSourceSearchError("");
      const hits = await api.searchSources(query);
      if (selectedIdRef.current !== matterId) return;
      setSourceHits(hits);
      setSourceSearchDone(true);
      setSelectedCitation(hits[0] ?? null);
    } catch (error) {
      if (selectedIdRef.current === matterId) setSourceSearchError(getError(error));
    } finally {
      setSourceSearchLoading(false);
    }
  }

  function openCitation(citation: Citation) {
    setSelectedCitation(citation);
    setDrawerOpen(true);
  }

  async function copyCitation() {
    if (!sourceDetail) return;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(`${citationLabel(sourceDetail)}\n${sourceDetail.content}\n${sourceDetail.url ?? ""}`);
      setNotice("Đã sao chép nguyên văn nguồn luật từ API.");
    } catch {
      setNotice("Không thể sao chép. Vui lòng sao chép thủ công.");
    }
  }

  function exportReport() {
    if (!selectedMatter) return;
    const lines = [
      "VN TAX COPILOT - BAO CAO TRA CUU",
      `Ma ho so: ${selectedMatter.id}`,
      `Ten ho so: ${selectedMatter.name}`,
      `Khach hang: ${selectedMatter.company}`,
      `Sac thue: ${selectedMatter.tax}`,
      `Nam ap dung: ${year}`,
      "",
      "LICH SU TRA CUU DA LUU TREN BACKEND",
      ...history.flatMap((item) => [
        `\nCau hoi: ${item.question}`,
        `Thoi gian: ${item.created_at}`,
        `Trang thai: ${reviewLabel(item.review_status)}`,
        `Tra loi: ${item.answer ?? "Chua co cau tra loi AI"}`,
        ...item.warnings.map((warning) => `Canh bao: ${warning}`),
        ...item.citations.map((c) => `Can cu: ${citationLabel(c)} [source_id=${c.source_id}]`),
      ]),
      "",
      "Tai lieu tra cuu, khong thay the viec tham dinh phap ly.",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bao-cao-${selectedMatter.id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    setNotice("Đã xuất báo cáo từ lịch sử API.");
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
              disabled={creatingMatter}
              title="Tạo hồ sơ mới"
            >
              +
            </button>
          </div>

          <button className="new-matter-button" onClick={createMatter}
              disabled={creatingMatter}>
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
            {loadingMatters && <div className="empty-state" role="status">Đang tải danh sách hồ sơ...</div>}
            {mattersError && <div className="empty-state" role="alert" style={{ color: "#dc2626" }}>{mattersError}</div>}
            {!loadingMatters && !mattersError && filteredMatters.length === 0 && (
              <div className="empty-state">{search.trim() ? "Không tìm thấy hồ sơ phù hợp." : "Chưa có hồ sơ nào."}</div>
            )}
            {filteredMatters.map((matter) => (
              <button
                key={matter.id}
                className={`matter-card ${
                  selectedId === matter.id ? "selected" : ""
                }`}
                onClick={() => {
                  setSelectedId(matter.id);
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
                      matter.status === "Lưu trữ" ? "pending" : ""
                    }`}
                  >
                    {matter.status}
                  </span>
                </div>
              </button>
            ))}

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
              LỊCH SỬ TRA CỨU TRONG HỒ SƠ
              <span />
            </div>

            <div className="ai-intro">
              <div className="ai-avatar">AI</div>
              <div className="message-content">
                <div className="message-author">
                  VN Tax Copilot <span>Tra cứu pháp lý</span>
                </div>
                <div className="message-bubble">
                  Nhập câu hỏi để tra cứu căn cứ pháp lý và lưu vào lịch sử hồ sơ.
                  Backend hiện chưa sinh câu trả lời AI tự động; mọi kết quả cần được chuyên viên kiểm tra.
                </div>
              </div>
            </div>

            {!selectedId && !loadingMatters && (
              <div className="empty-state">Hãy chọn hoặc tạo hồ sơ để bắt đầu.</div>
            )}
            {historyLoadingId === selectedId && selectedId && (
              <div className="empty-state" role="status">Đang tải lịch sử tra cứu...</div>
            )}
            {historyErrors[selectedId] && (
              <div className="empty-state" role="alert" style={{ color: "#dc2626" }}>
                Không thể tải lịch sử: {historyErrors[selectedId]}
              </div>
            )}
            {selectedId && historyLoadingId !== selectedId && !historyErrors[selectedId] && history.length === 0 && (
              <div className="empty-state">Hồ sơ này chưa có lượt tra cứu nào được lưu.</div>
            )}

            {history.map((item) => (
              <Fragment key={item.id}>
                <div className="message-row user-message">
                  <div className="message-content">
                    <div className="message-bubble">{item.question}</div>
                  </div>
                </div>
                <div className="message-row ai-message">
                  <div className="ai-avatar small">AI</div>
                  <div className="message-content">
                    <div className="message-author">
                      VN Tax Copilot <span>{reviewLabel(item.review_status)}</span>
                    </div>
                    <div className="message-bubble">
                      {item.answer?.trim() || "Backend chưa cung cấp câu trả lời AI cho lượt tra cứu này."}
                    </div>
                    {item.warnings.length > 0 && (
                      <div className="highlight-note" style={{ marginTop: 8 }} role="status">
                        <div className="note-heading">Lưu ý từ backend</div>
                        {item.warnings.map((warning, index) => <p key={index}>{warning}</p>)}
                      </div>
                    )}
                    {item.citations.length > 0 && (
                      <div className="citation-preview">
                        <div className="citation-label"><span>▤</span> CĂN CỨ TỪ API · CHƯA THẨM ĐỊNH</div>
                        {item.citations.map((citation, index) => (
                          <button
                            key={`${item.id}-${citation.source_id}-${index}`}
                            className="citation-link"
                            onClick={() => openCitation(citation)}
                          >
                            {citationLabel(citation)} <span>↗</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Fragment>
            ))}
            {sendingId === selectedId && (
              <div className="empty-state" role="status">Đang tra cứu và lưu lịch sử trên backend...</div>
            )}
            {sendErrors[selectedId] && (
              <div className="empty-state" role="alert" style={{ color: "#dc2626" }}>
                Không gửi được câu hỏi: {sendErrors[selectedId]}
              </div>
            )}
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
                <button type="submit" disabled={!draft.trim() || !selectedId || sendingId !== null || draft.trim().length > 2000}>
                  {sendingId === selectedId ? "Đang tra cứu..." : "Gửi câu hỏi"} <span>↑</span>
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
              >×</button>
            </div>

            <div className="legal-toolbar">
              <span className="verified-tag">NGUỒN API · CHƯA THẨM ĐỊNH</span>
              <button className="copy-button" onClick={copyCitation} disabled={!sourceDetail}>
                Sao chép
              </button>
            </div>

            <form onSubmit={searchLegalSources} style={{ padding: "12px 18px" }}>
              <label htmlFor="source-search" className="source-heading">TÌM VĂN BẢN PHÁP LUẬT</label>
              <div className="search-box" style={{ display: "flex", gap: 6, marginTop: 8 }}>
                <input
                  id="source-search"
                  aria-label="Tìm nguồn luật qua API"
                  placeholder="Nhập từ khóa hoặc điều luật..."
                  value={sourceQuery}
                  onChange={(event) => setSourceQuery(event.target.value)}
                  maxLength={500}
                  style={{ minWidth: 0, flex: 1 }}
                />
                <button type="submit" disabled={sourceSearchLoading || !sourceQuery.trim()}>
                  {sourceSearchLoading ? "Đang tìm" : "Tìm"}
                </button>
              </div>
            </form>

            {sourceSearchError && (
              <div className="empty-state" role="alert" style={{ color: "#dc2626" }}>
                {sourceSearchError}
              </div>
            )}
            {sourceSearchDone && !sourceSearchLoading && sourceHits.length === 0 && (
              <div className="empty-state">Không tìm thấy nguồn luật phù hợp trong cơ sở dữ liệu.</div>
            )}
            {sourceHits.length > 0 && (
              <div style={{ padding: "0 18px 10px" }}>
                <div className="source-heading">NGUỒN TÌM ĐƯỢC ({sourceHits.length})</div>
                {sourceHits.map((hit) => (
                  <div className="citation-preview" key={hit.source_id}>
                    <button className="citation-link" onClick={() => openCitation(hit)}>
                      {hit.citation_path || citationLabel(hit)} ↗
                    </button>
                    {hit.snippet && <p style={{ fontSize: 12, margin: "6px 0" }}>{hit.snippet}</p>}
                  </div>
                ))}
              </div>
            )}

            {!selectedCitation && !sourceLoading && (
              <div className="legal-content">
                <h3>Chưa chọn nguồn luật</h3>
                <p>Gửi câu hỏi hoặc tìm nguồn luật ở phía trên để xem điều khoản thật từ backend.</p>
                <div className="highlight-note">
                  <div className="note-heading"><span>i</span> Lưu ý pháp lý</div>
                  Không sử dụng nội dung minh họa làm căn cứ pháp luật. Mọi kết quả tra cứu cần được chuyên viên đối chiếu trước khi sử dụng.
                </div>
              </div>
            )}
            {sourceLoading && (
              <div className="empty-state" role="status">Đang tải nguyên văn điều luật...</div>
            )}
            {sourceError && (
              <div className="empty-state" role="alert" style={{ color: "#dc2626" }}>
                Không tải được nguồn luật: {sourceError}
              </div>
            )}
            {sourceDetail && (
              <>
                <div className="law-card">
                  <div className="law-icon">§</div>
                  <div>
                    <span className="law-type">{sourceDetail.doc_type || "VĂN BẢN PHÁP LUẬT"}</span>
                    <h3>{sourceDetail.title || sourceDetail.article_title || "Nguồn luật"}</h3>
                    <p>Số {sourceDetail.legal_identifier || "Chưa có số hiệu"}</p>
                  </div>
                </div>
                <div className="legal-content">
                  <div className="article-meta">
                    <span>ĐIỀU KHOẢN TỪ CƠ SỞ DỮ LIỆU</span>
                    <span className="article-number">{sourceDetail.dieu ? `Điều ${sourceDetail.dieu}` : "Nguồn luật"}</span>
                  </div>
                  <h3>{sourceDetail.article_title || citationLabel(sourceDetail)}</h3>
                  <p style={{ whiteSpace: "pre-wrap" }}>{sourceDetail.content}</p>
                  <div className="highlight-note">
                    <div className="note-heading"><span>i</span> Lưu ý pháp lý</div>
                    Nguồn được trả về từ backend, chưa đồng nghĩa đã được chuyên viên thẩm định hoặc xác nhận hiệu lực.
                  </div>
                </div>
                <div className="source-details">
                  <div className="source-heading">THÔNG TIN NGUỒN</div>
                  <div className="source-row"><span>Loại văn bản</span><strong>{sourceDetail.doc_type}</strong></div>
                  <div className="source-row"><span>Số hiệu</span><strong>{sourceDetail.legal_identifier ?? "—"}</strong></div>
                  <div className="source-row"><span>Phiên bản</span><strong>{sourceDetail.version}</strong></div>
                  <div className="source-row"><span>Hiệu lực từ</span><strong>{sourceDetail.effective_date?.slice(0, 10) ?? "Chưa rõ"}</strong></div>
                  <div className="source-row"><span>Hiệu lực đến</span><strong>{sourceDetail.expiry_date?.slice(0, 10) ?? "Chưa rõ"}</strong></div>
                  <div className="source-row"><span>Sắc thuế hồ sơ</span><strong>{selectedMatter?.tax ?? "—"}</strong></div>
                  {sourceDetail.url && (
                    <div className="source-row">
                      <span>Văn bản gốc</span>
                      <a href={sourceDetail.url} target="_blank" rel="noopener noreferrer">Mở nguồn ↗</a>
                    </div>
                  )}
                </div>
              </>
            )}
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
            <span>{reviewLabel(latestHistory?.review_status)}. Cần đối chiếu nguồn pháp luật trước khi sử dụng.</span>
          </div>
        </div>
        {notice && <span className="notice-message" role="status">{notice}</span>}
        <div className="review-actions">
          <button className="reject-button" disabled title="Backend chưa cung cấp API từ chối kết quả">
            Từ chối
          </button>
          <button className="approve-button" disabled title="Backend chưa cung cấp API phê duyệt kết quả">
            ✓ Phê duyệt
          </button>
          <button className="export-button" onClick={exportReport} disabled={!selectedMatter}>
            ↓ Xuất báo cáo
          </button>
        </div>
      </footer>
    </main>
  );
}
