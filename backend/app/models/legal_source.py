"""
app/models/legal_source.py  –  BẢNG VĂN BẢN PHÁP LUẬT (CHỈ ĐỌC, do nhóm Data nạp dữ liệu)
==========================================================================================
Hai bảng này do nhóm 5 (feature/05-data-legal-registry, data_pipeline/registry/models.py – SCRUM-21) thiết kế
và nạp dữ liệu. Backend chỉ ĐỌC để: tìm kiếm điều luật, xem nguyên văn đoạn trích dẫn (Citation Drawer).

Tên bảng/cột phải KHỚP 100% với nhánh 05 (kể cả cột backend chưa dùng): nếu backend khởi động trước và tạo bảng
thiếu cột thì code nạp dữ liệu của nhóm 5 sẽ lỗi. Nhóm 5 đổi schema -> sửa file này theo.
    legal_documents : 1 văn bản (Luật / Nghị định / Thông tư / Công văn / chưa xác định)
    legal_chunks    : 1 đoạn đã bóc tách theo Điều -> Khoản -> Điểm
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Trạng thái hiệu lực (giá trị cột `status` ở cả 2 bảng)
LEGAL_STATUSES = ("CHUA_XAC_DINH", "CON_HIEU_LUC", "HET_HIEU_LUC", "SUA_DOI_BO_SUNG", "BI_THAY_THE")
STATUS_UNKNOWN = "CHUA_XAC_DINH"


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # vd 48/2024/QH15
    title: Mapped[str] = mapped_column(String(500))
    # LUAT | NGHI_DINH | THONG_TU | CONG_VAN | UNKNOWN
    doc_type: Mapped[str] = mapped_column(String(50), default="UNKNOWN", index=True)
    # 1 Luật > 2 Nghị định > 3 Thông tư > 4 Công văn > 5 Chưa xác định (UNKNOWN)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=5)
    issuer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=STATUS_UNKNOWN, index=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    amends_doc_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    replaces_doc_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # Giống nhóm 5 (datetime.utcnow): giờ UTC không kèm múi giờ
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow_naive,
                                                        onupdate=_utcnow_naive)

    chunks: Mapped[list["LegalChunk"]] = relationship(back_populates="document")


class LegalChunk(Base):
    __tablename__ = "legal_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("legal_documents.id"), index=True)
    article_number: Mapped[str] = mapped_column(String(20), index=True)   # "9", "1a"
    article_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    article_intro: Mapped[str | None] = mapped_column(Text, nullable=True)  # câu mở đầu của Điều
    # Chuỗi để giữ hậu tố chữ ("1a", "2a"). "0" = đoạn không thuộc Khoản nào.
    clause_number: Mapped[str] = mapped_column(String(20), default="0", index=True)
    clause_intro: Mapped[str | None] = mapped_column(Text, nullable=True)   # câu mở đầu của Khoản
    point_letter: Mapped[str | None] = mapped_column(String(10), default="")  # "" = không có Điểm
    citation_path: Mapped[str] = mapped_column(String(500))                # "Điểm a, Khoản 1, Điều 9, 48/2024/QH15"
    content: Mapped[str] = mapped_column(Text)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=5)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=STATUS_UNKNOWN)
    version: Mapped[str] = mapped_column(String(50), default="1.0")

    document: Mapped[LegalDocument] = relationship(back_populates="chunks")
