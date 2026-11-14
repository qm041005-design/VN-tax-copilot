import re
import unicodedata
from typing import Optional

HIERARCHY_LEVELS = {
    "LUAT": 1,
    "NGHI_DINH": 2,
    "THONG_TU": 3,
    "CONG_VAN": 4,
    "UNKNOWN": 5,
}

DOC_TYPE_ALIASES = {
    "LUAT": "LUAT",
    "BO LUAT": "LUAT",
    "NGHI DINH": "NGHI_DINH",
    "THONG TU": "THONG_TU",
    "THONG TU LIEN TICH": "THONG_TU",
    "CONG VAN": "CONG_VAN",
}


def normalize_doc_type(doc_type: Optional[str]) -> str:
    """Chuẩn hóa loại văn bản; trả về 'UNKNOWN' nếu rỗng hoặc chưa xác định."""
    if not doc_type or not isinstance(doc_type, str) or not doc_type.strip():
        return "UNKNOWN"

    normalized = unicodedata.normalize("NFD", doc_type.strip())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = normalized.replace("đ", "d").replace("Đ", "D").upper()
    normalized = re.sub(r"[_\-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if normalized in DOC_TYPE_ALIASES:
        return DOC_TYPE_ALIASES[normalized]

    for alias, canonical in DOC_TYPE_ALIASES.items():
        if normalized.startswith(alias + " ") or f" {alias} " in f" {normalized} ":
            return canonical

    return "UNKNOWN"


def get_hierarchy_level(doc_type: Optional[str]) -> int:
    canonical_type = normalize_doc_type(doc_type)
    return HIERARCHY_LEVELS.get(canonical_type, HIERARCHY_LEVELS["UNKNOWN"])