"""
app/api/v1/sources.py  –  TÌM KIẾM ĐIỀU LUẬT & XEM NGUYÊN VĂN NGUỒN
=================================================================
    GET /api/v1/sources/search?q=...&doc_type=LUAT&as_of=2026-03-15&limit=10   -> list[SourceHit]
    GET /api/v1/sources/{source_id}                                            -> SourceDetail (Citation Drawer)
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.source import SourceDetail, SourceHit
from app.services import source_service
from app.schemas.matter import TaxType

router = APIRouter(prefix="/sources", tags=["Sources (Nguồn luật)"], dependencies=[Depends(get_current_user)])


@router.get("/search", response_model=list[SourceHit], summary="Tìm đoạn luật theo từ khóa")
def search_sources(
    q: str = Query(min_length=1, max_length=500, description="Từ khóa / câu hỏi"),
    doc_type: str | None = Query(default=None, max_length=50, description="LUAT | NGHI_DINH | THONG_TU | CONG_VAN"),
    as_of: date | None = Query(default=None, description="Chỉ lấy văn bản còn hiệu lực tại ngày này"),
    limit: int = Query(default=10, ge=1, le=50),
    tax_type: TaxType | None = None,
    tax_period: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db),
):
    try:
        rows = source_service.search(db, q, doc_type, as_of, limit,
                                     tax_type=tax_type.value if tax_type else None, tax_period=tax_period)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return [source_service.to_hit(c) for c, _ in rows]


@router.get("/{source_id}", response_model=SourceDetail, summary="Xem nguyên văn đoạn luật được trích dẫn")
def get_source(source_id: int, db: Session = Depends(get_db)):
    chunk = source_service.get_chunk(db, source_id)
    if chunk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nguồn luật")
    return source_service.to_detail(chunk)
