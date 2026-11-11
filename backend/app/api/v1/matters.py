"""
app/api/v1/matters.py  –  CÁC ENDPOINT HTTP CỦA HỒ SƠ VỤ VIỆC
=============================================================
Tầng "API": nhận request HTTP -> kiểm tra dữ liệu (nhờ schema) -> gọi service -> trả JSON.
File này KHÔNG chứa logic DB; chỉ "nối dây". Logic nằm ở app/services/matter_service.py.

Mọi route bắt đầu bằng /api/v1/matters (prefix "/api/v1" gắn ở api/v1/__init__.py).

Hai dependency được tiêm vào hầu hết endpoint:
    db   = Depends(get_db)           -> phiên làm việc DB cho request này
    user = Depends(get_current_user) -> ai đang gọi (user_id, tenant_id)

Bảng route:
    POST   /matters                 tạo hồ sơ               -> 201
    GET    /matters                 danh sách (lọc/phân trang)
    GET    /matters/{id}            xem chi tiết            -> 404 nếu không có / khác tenant
    PATCH  /matters/{id}            sửa một phần
    DELETE /matters/{id}            archive (xóa mềm)
    POST   /matters/{id}/history    lưu 1 lượt tra cứu      -> 201
    GET    /matters/{id}/history    xem lịch sử tra cứu (header X-Total-Count = tổng số)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.matter import (HistoryCreate, HistoryOut, MatterCreate, MatterList, MatterOut,
                                MatterUpdate)
from app.services import matter_service as svc

# tags: gom nhóm các endpoint trên trang Swagger
router = APIRouter(prefix="/matters", tags=["Matters (Hồ sơ vụ việc)"])


def _get_or_404(db: Session, user: CurrentUser, matter_id: uuid.UUID):
    """Hàm phụ: lấy hồ sơ, không có (hoặc thuộc tenant khác) thì ném lỗi 404 tiếng Việt."""
    matter = svc.get_matter(db, user, matter_id)
    if matter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ vụ việc")
    return matter


@router.post("", response_model=MatterOut, status_code=status.HTTP_201_CREATED, summary="Tạo hồ sơ vụ việc")
def create_matter(data: MatterCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    # `data` đã được Pydantic kiểm tra hợp lệ trước khi vào đây (sai -> tự trả 422)
    return svc.create_matter(db, user, data)


@router.get("", response_model=MatterList, summary="Danh sách hồ sơ vụ việc")
def list_matters(
    # alias="status": tên tham số trên URL là `status`, đặt tên biến `status_` để khỏi trùng module `status`
    status_: str | None = Query(default=None, alias="status", pattern="^(active|archived)$"),
    q: str | None = Query(default=None, description="Tìm theo tên hồ sơ / khách hàng"),
    limit: int = Query(default=20, ge=1, le=100),   # tối đa 100 dòng/trang để tránh quá tải
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    items, total = svc.list_matters(db, user, status_, q, limit, offset)
    return MatterList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{matter_id}", response_model=MatterOut, summary="Chi tiết hồ sơ")
def get_matter(matter_id: uuid.UUID, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    # matter_id kiểu uuid.UUID: gửi chuỗi không phải UUID -> tự trả 422
    return _get_or_404(db, user, matter_id)


@router.patch("/{matter_id}", response_model=MatterOut, summary="Cập nhật hồ sơ")
def update_matter(matter_id: uuid.UUID, data: MatterUpdate, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(get_current_user)):
    return svc.update_matter(db, user, _get_or_404(db, user, matter_id), data)


@router.delete("/{matter_id}", response_model=MatterOut, summary="Lưu trữ (archive) hồ sơ - xóa mềm")
def archive_matter(matter_id: uuid.UUID, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return svc.archive_matter(db, user, _get_or_404(db, user, matter_id))


@router.post("/{matter_id}/history", response_model=HistoryOut, status_code=status.HTTP_201_CREATED,
             summary="Lưu một lượt tra cứu vào hồ sơ")
def add_history(matter_id: uuid.UUID, data: HistoryCreate, db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user)):
    return svc.add_history(db, user, _get_or_404(db, user, matter_id), data)


@router.get("/{matter_id}/history", summary="Lịch sử tra cứu của hồ sơ")
def list_history(matter_id: uuid.UUID, response: Response, limit: int = Query(default=20, ge=1, le=100),
                 offset: int = Query(default=0, ge=0), db: Session = Depends(get_db),
                 user: CurrentUser = Depends(get_current_user)):
    items, total = svc.list_history(db, user, _get_or_404(db, user, matter_id), limit, offset)
    # Trả mảng thuần cho dễ dùng; tổng số bản ghi đặt ở header để frontend phân trang
    response.headers["X-Total-Count"] = str(total)
    return [HistoryOut.model_validate(i) for i in items]
