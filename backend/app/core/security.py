"""
app/core/security.py  –  XÁC ĐỊNH "AI ĐANG GỌI API" (TẠM THỜI)
==============================================================
Mục đích:
    Cho mọi endpoint biết người gọi là ai (user_id) và thuộc tổ chức nào (tenant_id).

TÌNH TRẠNG HIỆN TẠI (Sprint 1-2) – CHỈ LÀ PLACEHOLDER:
    Chưa có đăng nhập thật. Client gửi 2 header HTTP:
        X-User-Id:   alice
        X-Tenant-Id: thtax
    Nếu không gửi thì mặc định "dev-user" / "thtax" (tiện test trên Swagger).

VÌ SAO VẪN LÀM SỚM:
    RFP yêu cầu cô lập dữ liệu theo tenant ở MỌI đường truy cập (SEC 01).
    Nên toàn bộ service đã lọc theo tenant_id ngay từ bây giờ.
    Sau này chỉ cần SỬA HÀM NÀY (đọc từ JWT/SSO thay vì header), các endpoint không phải đổi.

!! KHÔNG dùng cách header này khi lên production – ai cũng giả mạo được.
"""
from dataclasses import dataclass

from fastapi import Header


@dataclass
class CurrentUser:
    """Thông tin người gọi, truyền vào các hàm service."""
    user_id: str
    tenant_id: str


def get_current_user(
    x_user_id: str = Header(default="dev-user", description="ID người dùng (tạm thời)"),
    x_tenant_id: str = Header(default="thtax", description="ID tenant (tạm thời)"),
) -> CurrentUser:
    """Dependency FastAPI: đọc 2 header và trả về CurrentUser."""
    return CurrentUser(user_id=x_user_id, tenant_id=x_tenant_id)
