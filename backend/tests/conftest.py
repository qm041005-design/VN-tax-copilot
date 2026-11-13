"""
tests/conftest.py  –  THIẾT LẬP CHUNG CHO PYTEST
=================================================
File đặc biệt: pytest tự nạp trước khi chạy test.

- Ép các biến môi trường NGAY ĐẦU FILE, trước khi import app (cấu hình được đọc lúc import):
    DATABASE_URL -> SQLite file (test.db) để test không đụng tới PostgreSQL thật
                    (chạy được cả trên GitHub Actions không có DB).
    CORS_ORIGINS -> cố định để test CORS cho kết quả giống nhau trên mọi máy.
- Fixture `client`: trước MỖI test, xóa và tạo lại toàn bộ bảng -> các test độc lập nhau.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"  # phải đặt TRƯỚC khi import app
os.environ["APP_ENV"] = "dev"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
# Token khớp tests/helpers.py: token của <user> là "test-token-<user>-local"
os.environ["AUTH_TOKENS"] = "test-token-alice-local:alice:thtax,test-token-bob-local:bob:other"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:  # TestClient giả lập trình duyệt gọi API, không cần mở cổng thật
        yield c
