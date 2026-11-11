"""
app/core/security.py  –  XÁC ĐỊNH "AI ĐANG GỌI API" (BẢN TẠM, CHƯA CÓ ĐĂNG NHẬP)
==============================================================================
Mục đích:
    Cho mọi endpoint biết người gọi là ai (user_id) và thuộc tổ chức nào (tenant_id).

TÌNH TRẠNG HIỆN TẠI – CHỈ LÀ PLACEHOLDER, CHƯA AN TOÀN ĐỂ TRIỂN KHAI THẬT:
    Chưa có đăng nhập. Client tự khai 2 header HTTP:
        X-User-Id:   alice
        X-Tenant-Id: thtax
    Nếu không gửi thì mặc định "dev-user" / "thtax" (tiện thử trên Swagger).

    => Ai cũng khai được tenant của người khác, và không đăng nhập vẫn dùng được API.
       Dùng để phát triển và thử trong nhóm; KHÔNG đưa lên môi trường thật khi chưa thay bằng đăng nhập.

VÌ SAO VẪN LÀM TRƯỚC PHẦN CÔ LẬP TENANT:
    RFP yêu cầu cô lập dữ liệu theo tenant ở MỌI đường truy cập (SEC 01).
    Toàn bộ service đã lọc theo tenant_id ngay từ bây giờ, nên sau này chỉ cần SỬA HÀM NÀY
    (đọc người dùng từ token SSO/JWT đã kiểm tra chữ ký thay vì header), các endpoint không phải đổi.

TODO (sprint sau, cần thống nhất với nhóm):
    - Đăng nhập SSO + MFA (RFP SEC 01), token có chữ ký, thiếu/sai token -> 401.
    - Phân quyền theo vai trò: researcher / reviewer / admin / auditor.
    - Bỏ giá trị mặc định "dev-user"/"thtax" và bỏ đọc header tự khai.
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
    """Dependency FastAPI: đọc 2 header và trả về CurrentUser (chưa kiểm tra danh tính)."""
    return CurrentUser(user_id=x_user_id, tenant_id=x_tenant_id)
