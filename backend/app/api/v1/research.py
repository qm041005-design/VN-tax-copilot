"""
app/api/v1/research.py  –  TRA CỨU TRONG HỒ SƠ: tìm nguồn luật + lưu lịch sử
==========================================================================
    POST /api/v1/research   body ResearchRequest -> 201 ResearchResponse

Luồng: kiểm tra quyền ghi hồ sơ -> tìm đoạn luật -> lưu 1 dòng research_history (citations = nguồn tìm được)
-> trả cả bản ghi lịch sử lẫn danh sách nguồn.
Chưa nối LLM: answer = null. Không tìm thấy nguồn -> từ chối trả lời (abstention), ghi cảnh báo.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.matters import _get_writable_or_error
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.matter import HistoryCreate, HistoryOut
from app.schemas.source import ResearchRequest, ResearchResponse
from app.services import matter_service, source_service
from app.services.guarded_research_service import research_from_rows
from ai_engine.guardrails import redact_text, to_contract


def research_callbacks():
    """Server-only injection point. No configured providers => no generation."""
    return None, None

router = APIRouter(prefix="/research", tags=["Research (Tra cứu)"])

NO_SOURCE = "Không tìm thấy căn cứ pháp lý phù hợp – hệ thống không đưa ra câu trả lời."
NO_ANSWER_YET = "Chưa có câu trả lời AI; danh sách trích dẫn là căn cứ tìm được, chuyên viên cần tự đối chiếu."


@router.post("", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED,
             summary="Tra cứu trong hồ sơ và lưu vào lịch sử")
def research(data: ResearchRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user),
             callbacks=Depends(research_callbacks)):
    matter = _get_writable_or_error(db, user, data.matter_id)
    period = data.tax_period or matter.tax_period
    try:
        rows = source_service.search(db, data.question, data.doc_type, data.research_as_of, data.limit,
                                     tax_type=data.tax_type.value if data.tax_type else None, tax_period=period)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    hits = [source_service.to_hit(c) for c, _ in rows]
    assess, generate = callbacks
    result = research_from_rows(data.question, rows, tax_period=period, material_facts=data.material_facts,
                                assess=assess, generate=generate)
    warnings = ([] if hits else [NO_SOURCE]) + [f"{result.status}: {result.reason}"]
    warnings += [w for w in (result.message, *result.questions) if w]
    warnings.append("Nguồn tìm thấy chưa xác minh đầy đủ hiệu lực, chuyển tiếp và khả năng áp dụng.")
    if data.tax_type:
        warnings.append("Bộ lọc sắc thuế chỉ tìm văn bản đã được gán nhãn; nguồn chưa phân loại bị loại.")
    # Preserve candidate references in history for existing UI when no answer exists.
    # Once there is an answer, only keep its validated citation IDs.
    cited = [h for h in hits if h.source_id in result.citation_ids] if result.status == "draft" else hits
    history = matter_service.add_history(db, user, matter, HistoryCreate(
        question=redact_text(data.question).text, tax_type=data.tax_type,
        tax_period=redact_text(period).text if period else None,
        research_as_of=data.research_as_of.isoformat() if data.research_as_of else None,
        material_facts=redact_text(data.material_facts).text if data.material_facts else None, answer=result.answer,
        citations=[h.model_dump(include={"source_id", "title", "legal_identifier", "dieu", "khoan", "diem", "url"})
                   for h in cited],
        warnings=warnings,
    ))
    return ResearchResponse(history=HistoryOut.model_validate(history), sources=hits,
                            research_result=to_contract(result))
