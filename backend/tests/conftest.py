"""
tests/conftest.py  –  THIẾT LẬP CHUNG CHO PYTEST
=================================================
File đặc biệt: pytest tự nạp trước khi chạy test.

- Ép DATABASE_URL sang SQLite file (test.db) NGAY ĐẦU FILE, trước khi import app,
  để test không đụng tới PostgreSQL thật (chạy được cả trên GitHub Actions không có DB).
- Fixture `client`: trước MỖI test, xóa và tạo lại toàn bộ bảng -> các test độc lập nhau.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"  # phải đặt TRƯỚC khi import app

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
