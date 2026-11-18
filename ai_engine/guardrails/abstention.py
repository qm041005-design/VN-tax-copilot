"""Evidence gate before synthesis; retrieval scores are not probabilities."""
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class EvidenceAssessment:
    """Trusted upstream assessment for this query and passage, never user input.

    None means unknown. True must cover relevance AND sufficiency for the query;
    temporal applicability/conflicts must be resolved by the assessing component.
    """
    passage_id: str | int
    sufficient: bool | None = None


@dataclass(frozen=True)
class AbstentionDecision:
    should_abstain: bool
    reason: str
    message: str
    evidence_ids: tuple[str | int, ...] = ()


def decide_abstention(
    query: str,
    passages: Sequence[Mapping],
    assessments: Sequence[EvidenceAssessment] = (),
) -> AbstentionDecision:
    """Only allow synthesis with identifiable text and explicit sufficient evidence.

    Accepts BM25 passage_id/legal_identifier/text/score dictionaries. Duplicate
    IDs and duplicate assessments are ambiguous and fail closed. This does not
    validate the final answer's claims or citations.
    """
    def refuse(reason, message):
        return AbstentionDecision(True, reason, message)

    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        return refuse("empty_query", "Vui lòng nhập câu hỏi cần tra cứu.")
    if not passages:
        return refuse("no_evidence", "Chưa tìm thấy nguồn để trả lời có căn cứ.")
    by_id = {}
    for passage in passages:
        pid = passage.get("passage_id")
        if type(pid) not in (str, int) or (isinstance(pid, str) and not pid.strip()):
            return refuse("invalid_evidence", "Nguồn truy xuất thiếu định danh hợp lệ.")
        if pid in by_id:
            return refuse("ambiguous_evidence", "Nguồn truy xuất có định danh trùng lặp; cần kiểm tra lại.")
        by_id[pid] = passage
    seen = set()
    accepted = []
    for assessment in assessments:
        pid = assessment.passage_id
        if type(pid) not in (str, int) or pid in seen or pid not in by_id:
            return refuse("invalid_assessment", "Kết quả đánh giá nguồn không hợp lệ; cần kiểm tra lại.")
        seen.add(pid)
        passage = by_id[pid]
        if assessment.sufficient is True and all(
            isinstance(passage.get(key), str) and passage[key].strip()
            for key in ("text", "legal_identifier")
        ):
            accepted.append(pid)
    if not accepted:
        return refuse("insufficient_evidence", "Chưa đủ căn cứ đã được đánh giá để trả lời. Vui lòng bổ sung thông tin hoặc chuyển chuyên gia thẩm định.")
    return AbstentionDecision(False, "evidence_available", "", tuple(accepted))
