"""
app/models/audit.py  –  BẢNG NHẬT KÝ KIỂM TOÁN (audit_logs)
===========================================================
Mục đích:
    Ghi lại "AI đã làm GÌ, LÚC NÀO, với ĐỐI TƯỢNG NÀO". RFP yêu cầu (SEC 04, DAT 04):
    log truy cập/thay đổi, thời gian UTC, có mã định danh ổn định.

Mỗi lần tạo / sửa / archive hồ sơ hoặc lưu lịch sử tra cứu, service sẽ thêm 1 dòng vào đây.
Bảng này CHỈ THÊM, không sửa/xóa (nguyên tắc audit log).
Sprint sau có thể bổ sung: ghi cả hành động ĐỌC, export DOCX/PDF, đổi quyền...
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base_mixins import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(64))            # user_id người thực hiện
    action: Mapped[str] = mapped_column(String(64))           # vd: matter.create, matter.update, history.create
    resource_type: Mapped[str] = mapped_column(String(32))    # loại đối tượng: matter | research_history
    resource_id: Mapped[str] = mapped_column(String(64))      # ID đối tượng bị tác động
    detail: Mapped[dict] = mapped_column(JSON, default=dict)  # thông tin thêm (vd các trường đã sửa)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
