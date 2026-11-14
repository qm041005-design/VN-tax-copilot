"""
app/api/v1/research.py  –  TRA CỨU TRONG HỒ SƠ: tìm nguồn luật + lưu lịch sử
==========================================================================
    POST /api/v1/research   body ResearchRequest -> 201 ResearchResponse

Luồng: kiểm tra quyền ghi hồ sơ -> tìm đoạn luật -> lưu 1 dòng research_history (citations = nguồn tìm được)
-> trả cả bản ghi lịch sử lẫn danh sách nguồn.
Chưa nối LLM: answer = null. Không tìm thấy nguồn -> từ chối trả lời (abstention), ghi cảnh báo.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.matters import _get_writable_or_error
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.matter import HistoryCreate, HistoryOut
from app.schemas.source import ResearchRequest, ResearchResponse
from app.services import matter_service, source_service

router = APIRouter(prefix="/research", tags=["Research (Tra cứu)"])

NO_SOURCE = "Không tìm thấy căn cứ pháp lý phù hợp – hệ thống không đưa ra câu trả lời."
NO_ANSWER_YET = "Chưa có câu trả lời AI; danh sách trích dẫn là căn cứ tìm được, chuyên viên cần tự đối chiếu."


@router.post("", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED,
             summary="Tra cứu trong hồ sơ và lưu vào lịch sử")
def research(data: ResearchRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    matter = _get_writable_or_error(db, user, data.matter_id)
    hits = [source_service.to_hit(c)
            for c, _ in source_service.search(db, data.question, data.doc_type, data.research_as_of, data.limit)]
    # shortcut: answer luôn null; nối pipeline AI (nhóm 6/7 + prompt nhóm 1) để sinh câu trả lời có trích dẫn.
    history = matter_service.add_history(db, user, matter, HistoryCreate(
        question=data.question, tax_type=data.tax_type, tax_period=data.tax_period,
        research_as_of=data.research_as_of.isoformat() if data.research_as_of else None,
        material_facts=data.material_facts, answer=None,
        citations=[h.model_dump(include={"source_id", "title", "legal_identifier", "dieu", "khoan", "diem", "url"})
                   for h in hits],
        warnings=[NO_ANSWER_YET if hits else NO_SOURCE],
    ))
    return ResearchResponse(history=HistoryOut.model_validate(history), sources=hits)
