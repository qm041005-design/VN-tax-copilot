from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# METADATA DAT-01: Thông tin văn bản luật
class LegalDocument(Base):
    __tablename__ = 'legal_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_code = Column(String(100), unique=True, nullable=False, index=True)  # VD: 38/2019/QH14
    title = Column(String(500), nullable=False)                              # VD: Luật Quản lý thuế 2019
    doc_type = Column(String(50), nullable=False)                            # Luật, Nghị định, Thông tư, Công văn
    hierarchy_level = Column(Integer, nullable=False, default=4)             # Thứ bậc hiệu lực (1, 2, 3, 4)
    issuer = Column(String(200))                                             # Quốc hội, Chính phủ, Bộ Tài chính...
    issue_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("LegalChunk", back_populates="document", cascade="all, delete-orphan")


# ĐOẠN TRÍCH DAT-02: Bóc tách chi tiết từng Điều - Khoản - Điểm
class LegalChunk(Base):
    __tablename__ = 'legal_chunks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey('legal_documents.id'), nullable=False, index=True)
    
    article_number = Column(Integer, nullable=False)   # Số Điều
    article_title = Column(String(300))                 # Tiêu đề Điều
    clause_number = Column(Integer, default=0)          # Số Khoản
    point_letter = Column(String(5), default='')        # Ký hiệu Điểm (a, b, c...)

    citation_path = Column(String(255), nullable=False) # VD: "Điểm a, Khoản 2, Điều 16, Luật 38/2019/QH14"
    content = Column(Text, nullable=False)              # Nội dung trích dẫn
    hierarchy_level = Column(Integer, nullable=False)   # Trọng số ưu tiên (kế thừa từ văn bản)

    document = relationship("LegalDocument", back_populates="chunks")