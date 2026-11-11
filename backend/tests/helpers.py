"""
tests/helpers.py  –  HÀM DÙNG CHUNG CHO CÁC FILE TEST
=====================================================
auth(user, tenant) tạo 2 header định danh TẠM THỜI (X-User-Id, X-Tenant-Id) – xem app/core/security.py.
Khi có đăng nhập thật thì chỉ cần sửa hàm này (trả header Authorization) là các test giữ nguyên.
"""


def auth(user_id: str, tenant_id: str) -> dict:
    return {"X-User-Id": user_id, "X-Tenant-Id": tenant_id}
