"""
app/core/config.py  –  CẤU HÌNH TẬP TRUNG CỦA ỨNG DỤNG
=========================================================
Mục đích:
    Gom mọi thiết lập (địa chỉ database, tên app, môi trường chạy...) vào MỘT chỗ.
    Các file khác chỉ cần `from app.core.config import settings` rồi dùng
    `settings.database_url`, không tự đọc biến môi trường rải rác.

Cách giá trị được nạp (ưu tiên từ cao xuống thấp):
    1. Biến môi trường của hệ điều hành / docker-compose (vd: DATABASE_URL=...)
    2. File `.env` đặt cạnh thư mục backend (copy từ `.env.example`)
    3. Giá trị mặc định ghi ngay trong class bên dưới

Lưu ý bảo mật:
    KHÔNG ghi mật khẩu thật vào code hay commit file `.env` (đã nằm trong .gitignore).
    Mặc định bên dưới chỉ là mật khẩu dev trùng với docker-compose.yml.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Thông tin hiển thị trên trang Swagger (/docs)
    app_name: str = "VN Tax Research Copilot API"
    app_version: str = "0.1.0"

    # "dev" | "staging" | "prod" – dùng để bật/tắt tính năng theo môi trường sau này
    app_env: str = "dev"

    # Chuỗi kết nối PostgreSQL, định dạng:
    #   postgresql://<user>:<password>@<host>:<port>/<tên_db>
    # - Chạy local (backend trên máy, DB trong docker): host = localhost
    # - Chạy trong docker-compose: host = db (tên service), đã set sẵn trong docker-compose.yml
    database_url: str = "postgresql://vntax_admin:vntax_secret@localhost:5432/vntax_copilot"

    # --- CORS ---
    # Các origin của frontend được phép gọi trực tiếp backend từ trình duyệt, ngăn cách bằng dấu phẩy.
    # Ví dụ prod:  CORS_ORIGINS=https://copilot.example.com
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Xác thực tối thiểu (môi trường thử nghiệm) ---
    # Danh sách token cố định, mỗi mục dạng  <token>:<user_id>:<tenant_id>, ngăn cách bằng dấu phẩy.
    #   AUTH_TOKENS=tok-alice-xxxx:alice:thtax,tok-bob-yyyy:bob:other
    # Rỗng = không ai gọi được API (an toàn mặc định). Token phải >= 16 ký tự.
    auth_tokens: str = ""

    # env_file: đọc file .env; extra="ignore": bỏ qua biến lạ để không báo lỗi
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        """Chuỗi CORS_ORIGINS -> danh sách origin (bỏ khoảng trắng, bỏ phần tử rỗng)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_token_map(self) -> dict[str, tuple[str, str]]:
        """AUTH_TOKENS -> {token: (user_id, tenant_id)}. Mục sai định dạng / token ngắn -> lỗi khi khởi động."""
        result = {}
        for item in filter(None, (i.strip() for i in self.auth_tokens.split(","))):
            parts = [p.strip() for p in item.split(":")]
            if len(parts) != 3 or not all(parts) or len(parts[0]) < 16:
                raise ValueError(f"AUTH_TOKENS sai định dạng ở mục bắt đầu bằng '{item[:4]}…'")
            result[parts[0]] = (parts[1], parts[2])
        return result


# Tạo 1 đối tượng dùng chung toàn app (singleton đơn giản)
settings = Settings()
