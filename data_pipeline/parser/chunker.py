import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional


def combine_context(*parts: Optional[str]) -> str:
    return " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )


def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _has_raw_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _resolve_status(meta: Dict[str, Any]) -> str:
    explicit_status = meta.get("legal_status") or meta.get("status")
    if explicit_status and str(explicit_status).strip():
        return str(explicit_status).strip()

    raw_eff = meta.get("effective_date")
    if not _has_raw_value(raw_eff):
        return "CHUA_XAC_DINH"

    eff_dt = _to_datetime(raw_eff)
    if eff_dt is None:
        return "CHUA_XAC_DINH"

    raw_as_of = meta.get("as_of")
    if _has_raw_value(raw_as_of):
        ref_dt = _to_datetime(raw_as_of)
        if ref_dt is None:
            return "CHUA_XAC_DINH"
    else:
        ref_dt = datetime.now()

    raw_exp = meta.get("expiry_date")
    exp_dt: Optional[datetime] = None
    if _has_raw_value(raw_exp):
        exp_dt = _to_datetime(raw_exp)
        if exp_dt is None:
            return "CHUA_XAC_DINH"

    if ref_dt < eff_dt:
        return "CHUA_XAC_DINH"

    if exp_dt is not None and ref_dt >= exp_dt:
        return "HET_HIEU_LUC"

    return "CON_HIEU_LUC"


def extract_preamble(text: str) -> str:
    """Trích xuất đoạn mở đầu / căn cứ pháp lý nằm trước Điều đầu tiên."""
    if not text or not text.strip():
        return ""
    first_art = re.search(
        r"^[ \t]*Điều[ \t]+\d+[a-zA-ZđĐ]?[ \t]*[.:]",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not first_art:
        return text.strip()
    return text[: first_art.start()].strip()


def _build_metadata_fields(
    metadata: Optional[Dict[str, Any]],
    source_page: Optional[int],
    hierarchy_level: int,
    preamble: str = "",
) -> Dict[str, Any]:
    meta = metadata or {}
    return {
        "source_page": source_page if source_page is not None else meta.get("source_page"),
        "source_url": meta.get("source_url"),
        "doc_type": meta.get("doc_type", "UNKNOWN"),
        "hierarchy_level": hierarchy_level,
        "effective_date": meta.get("effective_date"),
        "expiry_date": meta.get("expiry_date"),
        "status": _resolve_status(meta),
        "ocr_quality_status": meta.get("ocr_quality_status", "RAW"),
        "expert_review_status": meta.get("expert_review_status", "PENDING"),
        "version": meta.get("version", "1.0"),
        "amends_doc_code": meta.get("amends_doc_code"),
        "replaces_doc_code": meta.get("replaces_doc_code"),
        "preamble": preamble or meta.get("preamble", ""),
    }


def chunk_legal_document(
    text: str,
    doc_code: str,
    hierarchy_level: int = 5,
    source_page: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    if not text or not text.strip():
        return chunks

    preamble_text = extract_preamble(text)
    base_meta = _build_metadata_fields(
        metadata,
        source_page,
        hierarchy_level,
        preamble=preamble_text,
    )

    article_pattern = re.compile(
        r"^[ \t]*Điều[ \t]+(\d+[a-zA-ZđĐ]?)[ \t]*[.:][ \t]*(.*)$",
        re.MULTILINE | re.IGNORECASE,
    )

    articles = list(article_pattern.finditer(text))
    if not articles:
        return chunks

    clause_pattern = re.compile(
        r"^[ \t]*(\d+[a-zA-ZđĐ]?)\.[ \t]+"
        r"(.*?)(?=^[ \t]*\d+[a-zA-ZđĐ]?\.[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    point_pattern = re.compile(
        r"^[ \t]*([a-zđ])\)[ \t]*"
        r"(.*?)(?=^[ \t]*[a-zđ]\)[ \t]*|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )

    for i, art_match in enumerate(articles):
        art_num = art_match.group(1).strip().lower()
        art_title = art_match.group(2).strip()

        body_start = art_match.end()
        body_end = articles[i + 1].start() if i + 1 < len(articles) else len(text)
        art_body = text[body_start:body_end].strip()

        if not art_body:
            continue

        clause_matches = list(clause_pattern.finditer(art_body))

        if clause_matches:
            art_intro = art_body[: clause_matches[0].start()].strip()

            for cl_match in clause_matches:
                cl_num = cl_match.group(1).strip().lower()
                cl_content = cl_match.group(2).strip()

                point_matches = list(point_pattern.finditer(cl_content))

                if point_matches:
                    clause_intro = cl_content[: point_matches[0].start()].strip()

                    for pt_match in point_matches:
                        pt_letter = pt_match.group(1).lower()
                        pt_content = pt_match.group(2).strip()

                        citation = (
                            f"Điểm {pt_letter}, "
                            f"Khoản {cl_num}, "
                            f"Điều {art_num}, "
                            f"{doc_code}"
                        )
                        full_text = combine_context(
                            art_intro,
                            clause_intro,
                            pt_content,
                        )

                        chunks.append(
                            {
                                "article_number": art_num,
                                "article_title": art_title,
                                "article_intro": art_intro,
                                "clause_number": cl_num,
                                "clause_intro": clause_intro,
                                "point_letter": pt_letter,
                                "citation_path": citation,
                                "content": f"{citation}: {full_text}",
                                **base_meta,
                            }
                        )
                else:
                    citation = f"Khoản {cl_num}, Điều {art_num}, {doc_code}"
                    full_text = combine_context(art_intro, cl_content)

                    chunks.append(
                        {
                            "article_number": art_num,
                            "article_title": art_title,
                            "article_intro": art_intro,
                            "clause_number": cl_num,
                            "clause_intro": "",
                            "point_letter": "",
                            "citation_path": citation,
                            "content": f"{citation}: {full_text}",
                            **base_meta,
                        }
                    )
        else:
            point_matches = list(point_pattern.finditer(art_body))

            if point_matches:
                art_intro = art_body[: point_matches[0].start()].strip()

                for pt_match in point_matches:
                    pt_letter = pt_match.group(1).lower()
                    pt_content = pt_match.group(2).strip()

                    citation = f"Điểm {pt_letter}, Điều {art_num}, {doc_code}"
                    full_text = combine_context(art_intro, pt_content)

                    chunks.append(
                        {
                            "article_number": art_num,
                            "article_title": art_title,
                            "article_intro": art_intro,
                            "clause_number": "0",
                            "clause_intro": "",
                            "point_letter": pt_letter,
                            "citation_path": citation,
                            "content": f"{citation}: {full_text}",
                            **base_meta,
                        }
                    )
            else:
                citation = f"Điều {art_num}, {doc_code}"

                chunks.append(
                    {
                        "article_number": art_num,
                        "article_title": art_title,
                        "article_intro": art_body,
                        "clause_number": "0",
                        "clause_intro": "",
                        "point_letter": "",
                        "citation_path": citation,
                        "content": f"{citation}: {art_body}",
                        **base_meta,
                    }
                )

    return chunks


def chunk_ocr_pages(
    pages: List[Dict[str, Any]],
    doc_code: str,
    hierarchy_level: int = 5,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Chạy trình phân tích cú pháp trên các trang OCR đã được đối chiếu:
    pages = [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}]
    Gán chính xác source_page cho từng chunk theo trang xuất hiện thực tế.
    """
    if not pages:
        return []

    sorted_pages = sorted(pages, key=lambda p: p["page"])
    full_parts: List[str] = []
    page_ranges: List[tuple[int, int, int]] = []
    cursor = 0

    for item in sorted_pages:
        page_num = int(item["page"])
        page_text = (item.get("text") or "").strip()
        if not page_text:
            continue
        if full_parts:
            full_parts.append("\n")
            cursor += 1
        start_idx = cursor
        full_parts.append(page_text)
        cursor += len(page_text)
        page_ranges.append((start_idx, cursor, page_num))

    combined_text = "".join(full_parts)
    if not combined_text.strip():
        return []

    def _find_page_for_offset(offset: int) -> int:
        for start_i, end_i, p_num in page_ranges:
            if start_i <= offset <= end_i:
                return p_num
        return page_ranges[0][2]

    chunks = chunk_legal_document(
        text=combined_text,
        doc_code=doc_code,
        hierarchy_level=hierarchy_level,
        source_page=page_ranges[0][2],
        metadata=metadata,
    )

    search_cursor = 0
    for ch in chunks:
        art_marker = f"Điều {ch['article_number']}"
        art_pos = combined_text.find(art_marker, search_cursor)
        if art_pos == -1:
            art_pos = combined_text.find(art_marker)

        target_pos = art_pos
        if art_pos != -1 and ch["clause_number"] != "0":
            cl_marker = f"{ch['clause_number']}."
            cl_pos = combined_text.find(cl_marker, art_pos)
            if cl_pos != -1:
                target_pos = cl_pos

        if target_pos != -1:
            ch["source_page"] = _find_page_for_offset(target_pos)
            search_cursor = target_pos

    return chunks