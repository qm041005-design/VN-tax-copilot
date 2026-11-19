"""
app/schemas/matter.py  –  "HỢP ĐỒNG" DỮ LIỆU VÀO/RA CỦA API (Pydantic)
=====================================================================
Schema ≠ Model:
    - Model  (app/models)  : cấu trúc BẢNG trong database.
    - Schema (file này)    : hình dạng JSON mà client GỬI LÊN (request) và NHẬN VỀ (response).
Pydantic tự động:
    * kiểm tra dữ liệu (thiếu trường, sai kiểu, rỗng... -> trả HTTP 422)
    * sinh tài liệu Swagger (kèm ví dụ `examples`)
    * chuyển model DB -> JSON khi trả response (nhờ from_attributes=True)

Quy ước đặt tên:  XxxCreate = body khi tạo;  XxxUpdate = body khi sửa (mọi trường tùy chọn);
                  XxxOut   = dữ liệu trả về.
Frontend (bạn số 9) có thể dựa vào các schema này để định nghĩa kiểu TypeScript.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class TaxType(str, Enum):
    """3 sắc thuế trong phạm vi RFP. Gửi giá trị khác -> bị từ chối (422)."""
    VAT = "VAT"  # Thuế GTGT
    CIT = "CIT"  # Thuế TNDN
    PIT = "PIT"  # Thuế TNCN


# Chuỗi bắt buộc có nội dung: pydantic BỎ khoảng trắng đầu/cuối TRƯỚC, rồi mới kiểm tra độ dài.
# -> "   " thành "" và bị từ chối (422); "  Hồ sơ A " được lưu là "Hồ sơ A".
# (Chỉ min_length=1 thì chuỗi toàn dấu cách vẫn lọt qua.) 255 khớp String(255) của cột DB.
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


# ----------------------------- MATTER -----------------------------
class MatterCreate(BaseModel):
    """Body của POST /api/v1/matters (tạo hồ sơ)."""
    title: NonBlankStr = Field(examples=["Khấu trừ VAT đầu vào quý 1/2026"])
    client_name: NonBlankStr = Field(examples=["Công ty TNHH ABC"])
    description: str | None = None
    tax_types: list[TaxType] = Field(default_factory=list)
    tax_period: str | None = Field(default=None, max_length=32, examples=["2026"])


class MatterUpdate(BaseModel):
    """
    Body của PATCH /api/v1/matters/{id}. Chỉ gửi trường nào muốn đổi; trường không gửi sẽ giữ nguyên.

    Phân biệt "không gửi" và "gửi null":
        - description, tax_period: cột DB cho phép NULL -> gửi null nghĩa là XÓA giá trị (hợp lệ).
        - title, client_name, tax_types: cột DB KHÔNG cho NULL -> gửi null bị từ chối 422
          (trước đây lọt xuống DB và gây lỗi 500).
    """
    title: NonBlankStr | None = None
    client_name: NonBlankStr | None = None
    description: str | None = None
    tax_types: list[TaxType] | None = None
    tax_period: str | None = Field(default=None, max_length=32)

    @field_validator("title", "client_name", "tax_types")
    @classmethod
    def not_null(cls, v, info):
        """Chỉ chạy khi client CÓ gửi trường này (trường không gửi không bị kiểm tra)."""
        if v is None:
            raise ValueError(f"{info.field_name} không được là null")
        return v


class MatterOut(BaseModel):
    """Một hồ sơ trả về cho client."""
    model_config = ConfigDict(from_attributes=True)  # cho phép đọc trực tiếp từ object SQLAlchemy

    id: uuid.UUID
    tenant_id: str
    title: str
    client_name: str
    description: str | None
    tax_types: list[str]
    tax_period: str | None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class MatterList(BaseModel):
    """Kết quả danh sách có phân trang: items + tổng số bản ghi để frontend vẽ nút trang."""
    items: list[MatterOut]
    total: int
    limit: int
    offset: int


# ------------------------ RESEARCH HISTORY ------------------------
class Citation(BaseModel):
    """
    Một trích dẫn pháp lý ở mức Điều – Khoản – Điểm (CIT 01 trong RFP).
    Cấu trúc này sẽ được nhóm AI (nhóm 7) và Frontend (Citation Drawer) dùng chung,
    nếu cần thêm trường (vd version, effective_from) thì sửa ở đây và báo cả nhóm.
    """
    source_id: str
    title: str | None = None
    legal_identifier: str | None = Field(default=None, examples=["48/2024/QH15"])
    dieu: str | None = None
    khoan: str | None = None
    diem: str | None = None
    url: str | None = None


class HistoryCreate(BaseModel):
    """Body của POST /api/v1/matters/{id}/history (lưu 1 lượt tra cứu)."""
    question: str = Field(min_length=1)
    tax_type: TaxType | None = None
    tax_period: str | None = Field(default=None, max_length=32)   # bỏ trống -> tự lấy kỳ thuế của hồ sơ
    research_as_of: str | None = Field(default=None, max_length=32)  # cột DB String(32): quá dài -> 422 thay vì 500
    material_facts: str | None = None
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        """min_length=1 vẫn cho qua chuỗi toàn dấu cách "   " -> chặn thêm ở đây."""
        if not v.strip():
            raise ValueError("question không được để trống")
        return v


class HistoryOut(BaseModel):
    """Một lượt tra cứu trả về cho client."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    matter_id: uuid.UUID
    actor: str
    question: str
    tax_type: str | None
    tax_period: str | None
    research_as_of: str | None
    material_facts: str | None
    answer: str | None
    citations: list[dict]
    warnings: list[str]
    review_status: str
    answer_version: int
    created_at: datetime
