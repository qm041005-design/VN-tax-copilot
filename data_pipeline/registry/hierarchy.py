HIERARCHY_LEVELS = {
    "LUAT": 1,         # Cấp cao nhất
    "NGHI_DINH": 2,
    "THONG_TU": 3,
    "CONG_VAN": 4      # Cấp hướng dẫn xử lý
}

def get_hierarchy_level(doc_type: str) -> int:
    clean_type = doc_type.strip().upper()
    if "LUẬT" in clean_type or "LUAT" in clean_type:
        return HIERARCHY_LEVELS["LUAT"]
    elif "NGHỊ ĐỊNH" in clean_type or "NGHI DINH" in clean_type:
        return HIERARCHY_LEVELS["NGHI_DINH"]
    elif "THÔNG TƯ" in clean_type or "THONG TU" in clean_type:
        return HIERARCHY_LEVELS["THONG_TU"]
    return HIERARCHY_LEVELS["CONG_VAN"]