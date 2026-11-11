"""
app/main.py  –  ĐIỂM KHỞI ĐỘNG CỦA ỨNG DỤNG (entry point)
=========================================================
Chạy bằng:  uvicorn app.main:app --reload
(`app.main:app` = biến `app` trong file app/main.py)

File này làm 3 việc:
    1. Tạo đối tượng FastAPI (kèm tiêu đề/mô tả cho trang Swagger /docs).
    2. Khi server khởi động: tạo các bảng trong DB nếu chưa có.
    3. Bật CORS, gắn router API v1 và endpoint /health.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# CORS: cho phép frontend (khác cổng, vd http://localhost:3000) gọi trực tiếp backend từ trình duyệt.
# Trình duyệt gửi request "preflight" (OPTIONS) trước các request POST/PATCH/DELETE hoặc có header
# tùy chỉnh (X-User-Id...); không có middleware này thì preflight trả 405 và request thật bị chặn.
# Origin được phép cấu hình bằng biến môi trường CORS_ORIGINS (không dùng "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # không dùng cookie
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    # X-User-Id / X-Tenant-Id: header định danh TẠM THỜI (xem core/security.py). Thiếu chúng ở đây thì
    # trình duyệt chặn preflight khi frontend gửi 2 header này. Khi có đăng nhập thật thì đổi thành "Authorization".
    allow_headers=["Content-Type", "X-User-Id", "X-Tenant-Id"],
    # Mặc định JS cross-origin KHÔNG đọc được header này; frontend cần nó để phân trang lịch sử tra cứu.
    expose_headers=["X-Total-Count"],
    max_age=600,  # trình duyệt nhớ kết quả preflight 10 phút, đỡ gọi OPTIONS lặp lại
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
