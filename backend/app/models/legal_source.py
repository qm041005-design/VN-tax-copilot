"""
app/models/legal_source.py  –  BẢNG VĂN BẢN PHÁP LUẬT (CHỈ ĐỌC, do nhóm Data nạp dữ liệu)
==========================================================================================
Hai bảng này do nhóm 5 (feature/05-data-legal-registry, data_pipeline/registry/models.py) thiết kế
và nạp dữ liệu. Backend chỉ ĐỌC để: tìm kiếm điều luật, xem nguyên văn đoạn trích dẫn (Citation Drawer).

Tên bảng/cột phải KHỚP 100% với nhánh 05. Nhóm 5 đổi schema -> sửa file này theo.
    legal_documents : 1 văn bản (Luật / Nghị định / Thông tư / Công văn)
    legal_chunks    : 1 đoạn đã bóc tách theo Điều -> Khoản -> Điểm
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # vd 48/2024/QH15
    title: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(50), index=True)                # LUAT | NGHI_DINH | THONG_TU | CONG_VAN
    hierarchy_level: Mapped[int] = mapped_column(Integer)                        # 1 = Luật (cao nhất) ... 4 = Công văn
    issuer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    amends_doc_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    chunks: Mapped[list["LegalChunk"]] = relationship(back_populates="document")


class LegalChunk(Base):
    __tablename__ = "legal_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("legal_documents.id"), index=True)
    article_number: Mapped[str] = mapped_column(String(20), index=True)   # "9", "14a"
    article_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    clause_number: Mapped[str | None] = mapped_column(String(20), default="0")  # Giữ 1a; 0 là không có Khoản
    point_letter: Mapped[str | None] = mapped_column(String(5), default="")  # "" = không có Điểm
    citation_path: Mapped[str] = mapped_column(String(500))                # "Điểm a, Khoản 1, Điều 9, 48/2024/QH15"
    content: Mapped[str] = mapped_column(Text)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer)

    document: Mapped[LegalDocument] = relationship(back_populates="chunks")


class LegalDocumentTaxScope(Base):
    """Nhãn sắc thuế do người nhập dữ liệu xác minh; không suy ra từ tên văn bản."""
    __tablename__ = "legal_document_tax_scopes"
    doc_id: Mapped[int] = mapped_column(ForeignKey("legal_documents.id"), primary_key=True)
    tax_type: Mapped[str] = mapped_column(String(20), primary_key=True)
