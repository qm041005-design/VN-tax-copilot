"""
tests/helpers.py  –  HÀM DÙNG CHUNG CHO CÁC FILE TEST
=====================================================
auth(user, tenant) trả header Authorization: Bearer <token> của user đó (token khai trong conftest.py).
tenant chỉ để test dễ đọc; tenant thật lấy từ token phía server.
"""


def auth(user_id: str, tenant_id: str) -> dict:
    return {"Authorization": f"Bearer test-token-{user_id}-local"}
