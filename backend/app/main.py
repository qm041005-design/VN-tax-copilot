"""
app/main.py  –  ĐIỂM KHỞI ĐỘNG CỦA ỨNG DỤNG (entry point)
=========================================================
Chạy bằng:  uvicorn app.main:app --reload
(`app.main:app` = biến `app` trong file app/main.py)

File này làm 3 việc:
    1. Tạo đối tượng FastAPI (kèm tiêu đề/mô tả cho trang Swagger /docs).
    2. Khi server khởi động: tạo các bảng trong DB nếu chưa có.
    3. Gắn router API v1 và endpoint /health.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401  (bắt buộc import để Base biết có những bảng nào)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Code chạy 1 lần khi server bật (phần trước `yield`) và khi tắt (phần sau yield)."""
    # Sprint 1-2: tự tạo bảng cho nhanh. create_all KHÔNG sửa bảng đã tồn tại,
    # nên khi đổi cấu trúc cột phải chuyển sang Alembic migration (việc của sprint sau).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API backend cho Trợ lý AI tra cứu Thuế Việt Nam (VN-tax-copilot). "
                "Tài liệu Swagger tự động tại `/docs`, ReDoc tại `/redoc`.",
    lifespan=lifespan,
)
app.include_router(api_router)  # gắn toàn bộ /api/v1/...


@app.get("/health", tags=["System"], summary="Kiểm tra trạng thái service + kết nối DB")
def health():
    """
    Dùng cho: kiểm tra nhanh server sống chưa, DevOps (nhóm 3) dùng cho healthcheck Docker/CI.
    status = "ok" khi chạy được `SELECT 1` trên DB, ngược lại "degraded".
    """
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "version": settings.app_version}
