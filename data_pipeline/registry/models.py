from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    JSON,
    String,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    doc_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    doc_type = Column(String(50), nullable=False, default="UNKNOWN", index=True)
    hierarchy_level = Column(Integer, nullable=False, default=5)
    preamble = Column(Text, nullable=True)  # Đoạn mở đầu / căn cứ pháp lý trước Điều 1

    issuer = Column(String(200), nullable=True)
    source_url = Column(String(1000), nullable=True)
    total_pages = Column(Integer, nullable=True)
    tax_types = Column(JSON, nullable=False, default=list)  # VD: ["VAT", "TNDN", "TNCN"]

    issue_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # 3 nhóm trạng thái tách bạch rõ ý nghĩa:
    # 1. Trạng thái pháp lý: CON_HIEU_LUC, HET_HIEU_LUC, SUA_DOI_BO_SUNG, CHUA_CO_HIEU_LUC, CHUA_XAC_DINH
    status = Column(
        String(50),
        nullable=False,
        default="CHUA_XAC_DINH",
        index=True,
    )
    # 2. Trạng thái chất lượng OCR: RAW, VERIFIED, NEEDS_REVIEW
    ocr_quality_status = Column(
        String(50),
        nullable=False,
        default="RAW",
        index=True,
    )
    # 3. Trạng thái duyệt của chuyên gia: PENDING, APPROVED, REJECTED
    expert_review_status = Column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
    )

    version = Column(String(50), nullable=False, default="1.0")

    amends_doc_code = Column(String(100), nullable=True, index=True)
    replaces_doc_code = Column(String(100), nullable=True, index=True)

    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    chunks = relationship(
        "LegalChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    amendments = relationship(
        "LegalDocumentAmendment",
        foreign_keys="LegalDocumentAmendment.original_doc_id",
        back_populates="original_document",
        cascade="all, delete-orphan",
    )

    amended_by = relationship(
        "LegalDocumentAmendment",
        foreign_keys="LegalDocumentAmendment.amending_doc_id",
        back_populates="amending_document",
    )


class LegalChunk(Base):
    __tablename__ = "legal_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True,
    )

    # Dùng String đồng nhất cho cả Điều (1a, 14b) và Khoản (1, 1a, 2b)
    article_number = Column(String(20), nullable=False, index=True)
    article_title = Column(String(300), nullable=True)
    article_intro = Column(Text, nullable=True)
    clause_number = Column(String(20), nullable=False, default="0", index=True)
    clause_intro = Column(Text, nullable=True)
    point_letter = Column(String(10), default="")

    citation_path = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    
    source_page = Column(Integer, nullable=True)
    source_url = Column(String(1000), nullable=True)
    tax_types = Column(JSON, nullable=False, default=list)
    hierarchy_level = Column(Integer, nullable=False, default=5)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="CHUA_XAC_DINH")
    ocr_quality_status = Column(String(50), nullable=False, default="RAW")
    expert_review_status = Column(String(50), nullable=False, default="PENDING")
    version = Column(String(50), nullable=False, default="1.0")

    document = relationship("LegalDocument", back_populates="chunks")


class LegalDocumentAmendment(Base):
    __tablename__ = "legal_document_amendments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True,
    )
    amending_doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True,
    )

    amendment_type = Column(String(50), nullable=False, default="SUA_DOI")
    effective_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utc_now)

    original_document = relationship(
        "LegalDocument",
        foreign_keys=[original_doc_id],
        back_populates="amendments",
    )
    amending_document = relationship(
        "LegalDocument",
        foreign_keys=[amending_doc_id],
        back_populates="amended_by",
    )

    __table_args__ = (
        UniqueConstraint(
            "original_doc_id",
            "amending_doc_id",
            "amendment_type",
            name="uq_document_amendment",
        ),
    )