"""
app/services/matter_service.py  –  LOGIC NGHIỆP VỤ (làm việc với database)
==========================================================================
Tầng "service" chứa mọi thao tác DB: tạo, tìm, sửa hồ sơ, lưu lịch sử...
Endpoint (app/api) CHỈ nhận request rồi gọi hàm ở đây -> dễ test, dễ tái sử dụng,
và sau này module khác (vd export DOCX) có thể gọi lại mà không đi qua HTTP.

QUY TẮC VÀNG: mọi truy vấn đều có điều kiện `tenant_id == user.tenant_id`.
Nhờ vậy người của tổ chức A không bao giờ thấy dữ liệu của tổ chức B.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.models import AuditLog, Matter, MatterStatus, ResearchHistory
from app.schemas.matter import HistoryCreate, MatterCreate, MatterUpdate


def _audit(db: Session, user: CurrentUser, action: str, rtype: str, rid, detail: dict | None = None):
    """
    Thêm 1 dòng nhật ký kiểm toán vào session hiện tại.
    LƯU Ý: hàm này chỉ `add`, KHÔNG commit -> dòng audit được lưu CÙNG giao dịch với
    thao tác chính (hoặc cùng thành công, hoặc cùng bị hủy), không bao giờ lệch nhau.
    """
    db.add(AuditLog(tenant_id=user.tenant_id, actor=user.user_id, action=action,
                    resource_type=rtype, resource_id=str(rid), detail=detail or {}))


def create_matter(db: Session, user: CurrentUser, data: MatterCreate) -> Matter:
    """Tạo hồ sơ mới. tenant_id và created_by lấy từ người đang gọi (không tin client gửi)."""
    matter = Matter(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        title=data.title,
        client_name=data.client_name,
        description=data.description,
        tax_types=[t.value for t in data.tax_types],  # Enum -> chuỗi "VAT"/"CIT"/"PIT"
        tax_period=data.tax_period,
    )
    db.add(matter)
    db.flush()  # đẩy xuống DB để có matter.id dùng cho audit, nhưng CHƯA commit
    _audit(db, user, "matter.create", "matter", matter.id, {"title": matter.title})
    db.commit()          # lưu thật cả matter + audit
    db.refresh(matter)   # nạp lại để có đủ giá trị DB tự sinh (created_at...)
    return matter


def list_matters(db: Session, user: CurrentUser, status: str | None, q: str | None,
                 limit: int, offset: int) -> tuple[list[Matter], int]:
    """
    Danh sách hồ sơ của tenant, có lọc + phân trang.
      status : "active" | "archived" | None (tất cả)
      q      : từ khóa tìm trong tên hồ sơ hoặc tên khách hàng (không phân biệt hoa/thường)
      limit/offset : phân trang (lấy `limit` dòng, bỏ qua `offset` dòng đầu)
    Trả về (danh_sách, tổng_số_khớp_điều_kiện) – tổng số để frontend biết có bao nhiêu trang.
    """
    stmt = select(Matter).where(Matter.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Matter.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Matter.title.ilike(like) | Matter.client_name.ilike(like))
    # Đếm tổng trước khi cắt trang
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    # Hồ sơ cập nhật gần nhất lên đầu
    items = db.scalars(stmt.order_by(Matter.updated_at.desc()).limit(limit).offset(offset)).all()
    return list(items), total


def get_matter(db: Session, user: CurrentUser, matter_id: uuid.UUID) -> Matter | None:
    """
    Lấy 1 hồ sơ theo ID, CÓ lọc tenant.
    Hồ sơ của tenant khác -> trả None (endpoint sẽ báo 404, không báo 403)
    để người ngoài không biết được hồ sơ đó có tồn tại hay không.
    """
    return db.scalar(select(Matter).where(Matter.id == matter_id, Matter.tenant_id == user.tenant_id))


def update_matter(db: Session, user: CurrentUser, matter: Matter, data: MatterUpdate) -> Matter:
    """Sửa hồ sơ. Chỉ cập nhật các trường client thực sự gửi lên (exclude_unset=True)."""
    changes = data.model_dump(exclude_unset=True)
    # tax_types là list Enum -> đổi sang list chuỗi trước khi lưu JSON
    if "tax_types" in changes and changes["tax_types"] is not None:
        changes["tax_types"] = [t.value if hasattr(t, "value") else t for t in changes["tax_types"]]
    for k, v in changes.items():
        setattr(matter, k, v)
    _audit(db, user, "matter.update", "matter", matter.id, {"fields": list(changes)})
    db.commit()
    db.refresh(matter)
    return matter


def archive_matter(db: Session, user: CurrentUser, matter: Matter) -> Matter:
    """
    "Xóa mềm": chỉ đổi status -> archived, KHÔNG xóa dòng khỏi DB.
    Lý do: dữ liệu hồ sơ thuế cần giữ để kiểm toán (RFP: giữ hồ sơ nghiên cứu 24 tháng).
    """
    matter.status = MatterStatus.ARCHIVED.value
    _audit(db, user, "matter.archive", "matter", matter.id)
    db.commit()
    db.refresh(matter)
    return matter


def add_history(db: Session, user: CurrentUser, matter: Matter, data: HistoryCreate) -> ResearchHistory:
    """
    Lưu 1 lượt tra cứu (câu hỏi + trả lời + trích dẫn) vào hồ sơ.
    Nếu client không gửi tax_period thì lấy kỳ thuế mặc định của hồ sơ.
    Hàm này chỉ LƯU kết quả; việc sinh câu trả lời là của nhóm AI (Retrieval + Prompt).
    """
    item = ResearchHistory(
        matter_id=matter.id,
        tenant_id=user.tenant_id,
        actor=user.user_id,
        question=data.question,
        tax_type=data.tax_type.value if data.tax_type else None,
        tax_period=data.tax_period or matter.tax_period,
        research_as_of=data.research_as_of,
        material_facts=data.material_facts,
        answer=data.answer,
        citations=[c.model_dump() for c in data.citations],  # object Citation -> dict để lưu JSON
        warnings=data.warnings,
    )
    db.add(item)
    db.flush()
    _audit(db, user, "history.create", "research_history", item.id, {"matter_id": str(matter.id)})
    db.commit()
    db.refresh(item)
    return item


def list_history(db: Session, user: CurrentUser, matter: Matter, limit: int, offset: int):
    """Lịch sử tra cứu của 1 hồ sơ, mới nhất trước, có phân trang. Trả (danh_sách, tổng)."""
    stmt = select(ResearchHistory).where(
        ResearchHistory.matter_id == matter.id, ResearchHistory.tenant_id == user.tenant_id
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(ResearchHistory.created_at.desc()).limit(limit).offset(offset)).all()
    return list(items), total
