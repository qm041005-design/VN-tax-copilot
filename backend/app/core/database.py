"""
app/core/database.py  –  KẾT NỐI DATABASE (SQLAlchemy)
======================================================
Mục đích:
    Tạo "engine" (cổng nối tới PostgreSQL), "session" (phiên làm việc với DB)
    và `Base` (lớp cha của mọi model/bảng).

Các khái niệm cho người mới:
    - engine      : đối tượng quản lý kết nối (có connection pool) tới DB.
    - Session     : 1 "phiên" thao tác DB (thêm/sửa/xóa/truy vấn). Mỗi request HTTP dùng 1 session riêng.
    - Base        : mọi model (Matter, AuditLog...) kế thừa từ đây để SQLAlchemy biết tạo bảng gì.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite (dùng khi chạy pytest) cần thêm tham số này để dùng được trong nhiều thread.
# PostgreSQL không cần nên để rỗng.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

# pool_pre_ping=True: trước khi dùng 1 kết nối cũ, ping thử xem còn sống không
# -> tránh lỗi "connection closed" khi DB restart.
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)

# Nhà máy tạo Session. autocommit=False: ta tự gọi db.commit() khi muốn lưu thật.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Lớp cha của tất cả model. Mỗi class con = 1 bảng trong DB."""


def get_db():
    """
    Dependency của FastAPI: cấp 1 Session cho mỗi request, xong tự đóng.

    Cách dùng trong endpoint:   def ham(db: Session = Depends(get_db)): ...
    `yield` giúp: trước request -> mở session; sau request (kể cả lỗi) -> đóng session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
