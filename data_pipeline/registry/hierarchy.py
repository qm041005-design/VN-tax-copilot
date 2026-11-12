
import re
import unicodedata




HIERARCHY_LEVELS = {
    "LUAT": 1,
    "NGHI_DINH": 2,
    "THONG_TU": 3,
    "CONG_VAN": 4
}




def normalize_doc_type(doc_type: str) -> str:

    if not doc_type or not isinstance(doc_type, str):
        raise ValueError(
            "Loại văn bản (doc_type) không được để trống."
        )

    normalized = unicodedata.normalize(
        "NFD",
        doc_type.strip()
    )

    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    normalized = normalized.replace("đ", "d")
    normalized = normalized.replace("Đ", "D")

    normalized = normalized.upper()

    normalized = re.sub(
        r"[_\-]+",
        " ",
        normalized
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    return normalized.strip()




def get_hierarchy_level(doc_type: str) -> int:

    normalized = normalize_doc_type(doc_type)

    aliases = {
        "LUAT": "LUAT",
        "BO LUAT": "LUAT",

        "NGHI DINH": "NGHI_DINH",

        "THONG TU": "THONG_TU",

        "CONG VAN": "CONG_VAN"
    }

    canonical_type = aliases.get(normalized)

    if canonical_type is None:

        raise ValueError(
            f"Loại văn bản không xác định: '{doc_type}'. "
            f"Chỉ chấp nhận: "
            f"{', '.join(HIERARCHY_LEVELS.keys())}."
        )

    return HIERARCHY_LEVELS[canonical_type]
