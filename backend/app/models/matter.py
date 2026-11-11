"""
app/models/matter.py  –  ĐỊNH NGHĨA BẢNG: HỒ SƠ VỤ VIỆC & LỊCH SỬ TRA CỨU
==========================================================================
Model = class Python đại diện cho 1 bảng trong PostgreSQL.
Mỗi thuộc tính `Mapped[...] = mapped_column(...)` = 1 cột.

Có 2 bảng:
    1) matters           : Hồ sơ vụ việc (Matter Workspace – RES 08 trong RFP).
                           Vd: "Khấu trừ VAT đầu vào Q1/2026 – Công ty ABC".
    2) research_history  : Mỗi lần chuyên viên tra cứu trong 1 hồ sơ = 1 dòng
                           (câu hỏi + câu trả lời + trích dẫn). Bám DAT 03.

Quan hệ:  1 matter  --(có nhiều)-->  research_history
          Xóa matter thì lịch sử của nó cũng bị xóa (cascade).
          (Nhưng API hiện chỉ "archive" – xóa mềm – nên dữ liệu vẫn được giữ.)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_mixins import utcnow


class MatterStatus(str, enum.Enum):
    """Trạng thái hồ sơ. ARCHIVED = đã lưu trữ (xóa mềm), không hiện ở danh sách mặc định."""
    ACTIVE = "active"
    ARCHIVED = "archived"


class ReviewStatus(str, enum.Enum):
    """
    Vòng đời thẩm định của một câu trả lời (Figure 3 trong RFP):
        draft -> under_review -> approved | rejected   (và superseded khi có bản mới thay thế)
    Sprint này chỉ dùng 'draft'; các trạng thái còn lại để dành cho màn hình duyệt bài sau.
    """
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Matter(Base):
    """Bảng `matters` – một hồ sơ vụ việc của khách hàng."""
    __tablename__ = "matters"
    # Index ghép (tenant_id, status): tăng tốc câu truy vấn "danh sách hồ sơ active của tenant X"
    __table_args__ = (Index("ix_matters_tenant_status", "tenant_id", "status"),)

    # Khóa chính dạng UUID (chuỗi ngẫu nhiên duy nhất) – an toàn hơn số tự tăng 1,2,3...
    # vì người ngoài không đoán được ID của hồ sơ khác.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # Thuộc tổ chức nào. MỌI truy vấn phải lọc theo cột này (cô lập dữ liệu giữa các tenant).
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)

    title: Mapped[str] = mapped_column(String(255))          # Tên hồ sơ
    client_name: Mapped[str] = mapped_column(String(255))    # Tên khách hàng
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # Ghi chú dài (tùy chọn)

    # Danh sách sắc thuế liên quan, lưu dạng JSON: ["VAT", "CIT", "PIT"]  (GTGT / TNDN / TNCN)
    tax_types: Mapped[list] = mapped_column(JSON, default=list)

    # Kỳ tính thuế mặc định của hồ sơ, vd "2026" hoặc "2026-Q1". Dùng làm mặc định cho lịch sử tra cứu.
    tax_period: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default=MatterStatus.ACTIVE.value)
    created_by: Mapped[str] = mapped_column(String(64))  # user_id người tạo

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # onupdate=utcnow: mỗi lần UPDATE dòng này, SQLAlchemy tự cập nhật lại thời gian
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Truy cập nhanh matter.history -> danh sách các lượt tra cứu (mới nhất trước)
    history: Mapped[list["ResearchHistory"]] = relationship(
        back_populates="matter", cascade="all, delete-orphan", order_by="ResearchHistory.created_at.desc()"
    )


class ResearchHistory(Base):
    """Bảng `research_history` – mỗi lượt tra cứu được lưu trong một hồ sơ."""
    __tablename__ = "research_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # Khóa ngoại trỏ về matters.id. ondelete="CASCADE": xóa matter -> xóa luôn lịch sử.
    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id", ondelete="CASCADE"), index=True)

    # Lưu lại tenant_id ở đây nữa để lọc nhanh và làm lớp bảo vệ thứ hai
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(64))  # ai đã thực hiện tra cứu

    question: Mapped[str] = mapped_column(Text)  # câu hỏi của chuyên viên
    tax_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # VAT | CIT | PIT
    tax_period: Mapped[str | None] = mapped_column(String(32), nullable=True)  # kỳ tính thuế của câu hỏi

    # Ngày mà luật được xét hiệu lực ("research as of date" – RES 01). Vd "2026-03-15".
    # Lưu dạng chuỗi để cho phép giá trị chưa chắc chắn; AI/Retrieval team sẽ chuẩn hóa sau.
    research_as_of: Mapped[str | None] = mapped_column(String(32), nullable=True)

    material_facts: Mapped[str | None] = mapped_column(Text, nullable=True)  # tình tiết quan trọng
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)          # câu trả lời của Copilot

    # Danh sách trích dẫn, mỗi phần tử dạng:
    #   {"source_id": "...", "legal_identifier": "48/2024/QH15", "dieu": "9", "khoan": "1", "diem": "a", "url": "..."}
    citations: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)  # cảnh báo (vd "công văn chỉ áp dụng cá biệt")

    review_status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.DRAFT.value)
    answer_version: Mapped[int] = mapped_column(default=1)  # tăng khi có bản sửa (dành cho sprint sau)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    matter: Mapped[Matter] = relationship(back_populates="history")
