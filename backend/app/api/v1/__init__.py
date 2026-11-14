"""
app/api/v1/__init__.py  –  GOM TẤT CẢ ROUTER CỦA PHIÊN BẢN API v1
=================================================================
Mọi endpoint v1 nằm dưới tiền tố /api/v1. Có router mới (vd /research, /export)
thì: tạo file trong thư mục này, rồi thêm 1 dòng `api_router.include_router(...)` bên dưới.
Dùng "v1" để sau này đổi cấu trúc lớn có thể ra v2 mà không phá client cũ (ARC 02 – versioned APIs).
"""
from fastapi import APIRouter

from app.api.v1 import matters, research, sources

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(matters.router)
api_router.include_router(sources.router)
api_router.include_router(research.router)
