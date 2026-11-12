
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime


Base = declarative_base()




class LegalDocument(Base):

    __tablename__ = "legal_documents"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Thông tin nhận diện văn bản
    doc_code = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    title = Column(
        String(500),
        nullable=False
    )

    doc_type = Column(
        String(50),
        nullable=False,
        index=True
    )

    hierarchy_level = Column(
        Integer,
        nullable=False
    )

    # Metadata pháp lý
    issuer = Column(String(200))

    source_url = Column(String(1000))

    issue_date = Column(DateTime)

    effective_date = Column(DateTime)

    expiry_date = Column(DateTime, nullable=True)

    # Phiên bản văn bản
    version = Column(
        String(50),
        nullable=False,
        default="1.0"
    )

    
    amends_doc_code = Column(
        String(100),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Quan hệ với các đoạn trích
    chunks = relationship(
        "LegalChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    
    amendments = relationship(
        "LegalDocumentAmendment",
        foreign_keys="LegalDocumentAmendment.original_doc_id",
        back_populates="original_document",
        cascade="all, delete-orphan"
    )

    
    amended_by = relationship(
        "LegalDocumentAmendment",
        foreign_keys="LegalDocumentAmendment.amending_doc_id",
        back_populates="amending_document"
    )




class LegalChunk(Base):

    __tablename__ = "legal_chunks"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True
    )

    # Dùng String để hỗ trợ Điều 1a, 14b...
    article_number = Column(
        String(20),
        nullable=False,
        index=True
    )

    article_title = Column(String(300))

    clause_number = Column(
        Integer,
        default=0
    )

    point_letter = Column(
        String(5),
        default=""
    )

    # Đường dẫn trích dẫn pháp lý
    citation_path = Column(
        String(500),
        nullable=False
    )

    
    content = Column(
        Text,
        nullable=False
    )

    
    source_page = Column(
        Integer,
        nullable=True
    )

    hierarchy_level = Column(
        Integer,
        nullable=False
    )

    document = relationship(
        "LegalDocument",
        back_populates="chunks"
    )




class LegalDocumentAmendment(Base):

    __tablename__ = "legal_document_amendments"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    original_doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True
    )

    amending_doc_id = Column(
        Integer,
        ForeignKey("legal_documents.id"),
        nullable=False,
        index=True
    )

    amendment_type = Column(
        String(50),
        nullable=True
    )

    description = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    
    original_document = relationship(
        "LegalDocument",
        foreign_keys=[original_doc_id],
        back_populates="amendments"
    )

    
    amending_document = relationship(
        "LegalDocument",
        foreign_keys=[amending_doc_id],
        back_populates="amended_by"
    )

    __table_args__ = (
        UniqueConstraint(
            "original_doc_id",
            "amending_doc_id",
            name="uq_document_amendment"
        ),
    )
