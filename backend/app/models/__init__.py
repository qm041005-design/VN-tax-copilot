"""
Import tất cả model ở đây để khi `import app.models`, SQLAlchemy "biết" mọi bảng
và `Base.metadata.create_all()` (trong main.py) tạo đủ bảng.
Thêm model mới -> nhớ import vào file này.
"""
from app.models.audit import AuditLog  # noqa: F401
from app.models.matter import Matter, MatterStatus, ResearchHistory, ReviewStatus  # noqa: F401
from app.models.legal_source import LegalChunk, LegalDocument, LegalDocumentTaxScope  # noqa: F401
