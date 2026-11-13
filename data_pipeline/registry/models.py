from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    
    doc_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    doc_type = Column(String(50), nullable=False, default="UNKNOWN", index=True)
    hierarchy_level = Column(Integer, nullable=False, default=5)

    
    issuer = Column(String(200), nullable=True)
    source_url = Column(String(1000), nullable=True)
    total_pages = Column(Integer, nullable=True)

   
    issue_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(
        String(50),
        nullable=False,
        default="CON_HIEU_LUC",
        index=True,
    ) 
    version = Column(String(50), nullable=False, default="1.0")

   
    amends_doc_code = Column(String(100), nullable=True, index=True)
    replaces_doc_code = Column(String(100), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

   
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

    
    article_number = Column(String(20), nullable=False, index=True)
    article_title = Column(String(300), nullable=True)
    article_intro = Column(Text, nullable=True)
    clause_number = Column(Integer, default=0)
    clause_intro = Column(Text, nullable=True)
    point_letter = Column(String(10), default="")

  
    citation_path = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    
    source_page = Column(Integer, nullable=True)
    source_url = Column(String(1000), nullable=True)
    hierarchy_level = Column(Integer, nullable=False, default=5)
    effective_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="CON_HIEU_LUC")
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
    created_at = Column(DateTime, default=datetime.utcnow)

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