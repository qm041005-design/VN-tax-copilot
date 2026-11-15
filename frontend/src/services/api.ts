
const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

const TOKEN = process.env.NEXT_PUBLIC_DEV_API_TOKEN;

export type TaxType = "VAT" | "CIT" | "PIT";

export interface Matter {
  id: string;
  tenant_id: string;
  title: string;
  client_name: string;
  description: string | null;
  tax_types: TaxType[];
  tax_period: string | null;
  status: "active" | "archived";
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MatterList {
  items: Matter[];
  total: number;
  limit: number;
  offset: number;
}

export interface MatterCreate {
  title: string;
  client_name: string;
  description?: string | null;
  tax_types?: TaxType[];
  tax_period?: string | null;
}

export interface Citation {
  source_id: string;
  title: string | null;
  legal_identifier: string | null;
  dieu: string | null;
  khoan: string | null;
  diem: string | null;
  url: string | null;
}

export interface HistoryItem {
  id: string;
  matter_id: string;
  actor: string;
  question: string;
  tax_type: TaxType | null;
  tax_period: string | null;
  research_as_of: string | null;
  material_facts: string | null;
  answer: string | null;
  citations: Citation[];
  warnings: string[];
  review_status: string;
  answer_version: number;
  created_at: string;
}

export interface SourceHit extends Citation {
  citation_path: string;
  doc_type: string;
  hierarchy_level: number;
  effective_date: string | null;
  expiry_date: string | null;
  snippet: string;
}

export interface SourceDetail extends SourceHit {
  content: string;
  article_title: string | null;
  issuer: string | null;
  version: string;
  source_page: number | null;
}

export interface ResearchResponse {
  history: HistoryItem;
  sources: SourceHit[];
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  if (!TOKEN) {
    throw new Error("Chưa cấu hình token API thử nghiệm.");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;

    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((e) => e.msg).join("; ")
          : `API thất bại: HTTP ${response.status}`;

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getMatters: (q = "") =>
    apiRequest<MatterList>(
      `/matters?${new URLSearchParams({
        status: "active",
        q,
        limit: "100",
        offset: "0",
      })}`
    ),

  createMatter: (data: MatterCreate) =>
    apiRequest<Matter>("/matters", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMatter: (id: string) =>
    apiRequest<Matter>(`/matters/${encodeURIComponent(id)}`),

  getHistory: (id: string) =>
    apiRequest<HistoryItem[]>(
      `/matters/${encodeURIComponent(id)}/history`
    ),

  research: (data: {
    matter_id: string;
    question: string;
    tax_type?: TaxType;
    tax_period?: string;
    research_as_of?: string;
  }) =>
    apiRequest<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  searchSources: (query: string) =>
    apiRequest<SourceHit[]>(
      `/sources/search?${new URLSearchParams({ q: query })}`
    ),

  getSource: (id: string) =>
    apiRequest<SourceDetail>(
      `/sources/${encodeURIComponent(id)}`
    ),
};
