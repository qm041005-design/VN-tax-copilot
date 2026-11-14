"""
app/core/security.py  –  XÁC THỰC TỐI THIỂU CHO MÔI TRƯỜNG THỬ NGHIỆM
====================================================================
Client gửi header:   Authorization: Bearer <token>
Token được cấp sẵn trong biến môi trường AUTH_TOKENS (xem core/config.py), mỗi token gắn với
1 user_id + 1 tenant_id. Thiếu / sai token -> 401. tenant_id KHÔNG còn do client tự khai.

Trên Swagger (/docs): bấm nút "Authorize", dán token (không cần gõ chữ "Bearer").

TODO (sprint sau): SSO + MFA (RFP SEC 01), token có chữ ký/hết hạn, phân quyền theo vai trò
(researcher / reviewer / admin / auditor). Chỉ cần thay hàm get_current_user, endpoint giữ nguyên.
"""
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False, description="Token thử nghiệm cấp trong AUTH_TOKENS")
_TOKENS = settings.auth_token_map  # đọc 1 lần lúc khởi động; sai định dạng thì app không chạy


@dataclass
class CurrentUser:
    """Thông tin người gọi, truyền vào các hàm service."""
    user_id: str
    tenant_id: str


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    """Dependency FastAPI: kiểm tra Bearer token, trả về CurrentUser; sai/thiếu -> 401."""
    if cred is not None:
        # compare_digest: so sánh thời gian hằng, tránh đoán token qua thời gian phản hồi
        for token, (user_id, tenant_id) in _TOKENS.items():
            if secrets.compare_digest(token.encode(), cred.credentials.encode()):
                return CurrentUser(user_id=user_id, tenant_id=tenant_id)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập hoặc token không hợp lệ",
                        headers={"WWW-Authenticate": "Bearer"})
