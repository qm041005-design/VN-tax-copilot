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
    snippet: str


class SourceDetail(SourceHit):
    """Nguyên văn đoạn luật cho Citation Drawer (cột 3 giao diện)."""
    content: str
    article_title: str | None = None
    issuer: str | None = None
    version: str
    source_page: int | None = None


class ResearchRequest(BaseModel):
    """Body của POST /api/v1/research: tra cứu trong 1 hồ sơ, kết quả tự lưu vào lịch sử hồ sơ đó."""
    matter_id: uuid.UUID
    question: str = Field(min_length=1, max_length=2000, examples=["Thuế suất GTGT phổ thông là bao nhiêu?"])
    tax_type: TaxType | None = None
    tax_period: str | None = Field(default=None, max_length=32)
    research_as_of: date | None = Field(default=None, description="Chỉ lấy văn bản còn hiệu lực tại ngày này (YYYY-MM-DD)")
    material_facts: str | None = None
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
