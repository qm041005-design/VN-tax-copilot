"""
app/schemas/source.py  –  JSON VÀO/RA CỦA API TÌM KIẾM NGUỒN LUẬT & TRA CỨU (/sources, /research)
================================================================================================
SourceHit kế thừa Citation (schemas/matter.py) để frontend dùng CHUNG MỘT kiểu cho:
    - kết quả tìm kiếm, - phần tử `citations` trong lịch sử tra cứu, - Citation Drawer.
`source_id` = id đoạn luật (legal_chunks.id) dạng chuỗi -> gọi GET /api/v1/sources/{source_id} để xem nguyên văn.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator
from typing import Literal

from app.schemas.matter import Citation, HistoryOut, TaxType


class SourceHit(Citation):
    """Một đoạn luật tìm được (Điều/Khoản/Điểm) + đoạn trích ngắn để hiển thị trong danh sách."""
    citation_path: str = Field(examples=["Điểm a, Khoản 1, Điều 9, 48/2024/QH15"])
    doc_type: str = Field(examples=["LUAT"], description="LUAT | NGHI_DINH | THONG_TU | CONG_VAN | UNKNOWN")
    hierarchy_level: int = Field(description="1 Luật > 2 Nghị định > 3 Thông tư > 4 Công văn > 5 Chưa xác định")
    status: str = Field(examples=["CON_HIEU_LUC"],
                        description="CHUA_XAC_DINH | CON_HIEU_LUC | HET_HIEU_LUC | SUA_DOI_BO_SUNG | BI_THAY_THE")
    effective_date: datetime | None = None
    expiry_date: datetime | None = None
    source_page: int | None = Field(default=None, description="Số trang PDF đếm từ 1")
    version: str | None = None
    snippet: str


class SourceDetail(SourceHit):
    """Nguyên văn đoạn luật cho Citation Drawer (cột 3 giao diện)."""
    content: str
    article_title: str | None = None
    issuer: str | None = None
    version: str = Field(...)


class ResearchRequest(BaseModel):
    """Body của POST /api/v1/research: tra cứu trong 1 hồ sơ, kết quả tự lưu vào lịch sử hồ sơ đó."""
    matter_id: uuid.UUID
    question: str = Field(min_length=1, max_length=2000, examples=["Thuế suất GTGT phổ thông là bao nhiêu?"])
    tax_type: TaxType | None = None
    tax_period: str | None = Field(default=None, max_length=32)
    research_as_of: date | None = Field(
        default=None, description="Lọc theo ngày tra cứu khi thiếu kỳ thuế. Giữ ngày chưa biết ở dạng null."
    )
    material_facts: str | None = None
    clarification_scenario: Literal["goods_rate", "residency"] | None = None
    case_facts: dict[str, str] = Field(default_factory=dict, max_length=20)

    @field_validator("case_facts")
    @classmethod
    def bounded_case_facts(cls, values):
        allowed = {"goods_description", "transaction_type", "transaction_date", "presence_period", "accommodation", "foreign_residency"}
        if set(values) - allowed or any(len(value) > 2000 for value in values.values()):
            raise ValueError("case_facts contains unknown or oversized fields")
        return values

    doc_type: str | None = Field(default=None, max_length=50, examples=["LUAT"])
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question không được để trống")
        return v.strip()


class ResearchResponse(BaseModel):
    """`history` = bản ghi đã lưu vào hồ sơ; `sources` = các đoạn luật tìm được (cùng thứ tự với history.citations)."""
    history: HistoryOut
    sources: list[SourceHit]
    research_result: dict | None = None
