"""Deterministic data collection; does not decide tax rates or residency law."""
import unicodedata

QUESTIONS = {
    "goods_rate": {
        "goods_description": "Hàng hóa cụ thể là gì? Vui lòng mô tả tên, đặc tính và mục đích sử dụng; cung cấp mã phân loại nếu đã có.",
        "transaction_type": "Đây là giao dịch bán trong nước, nhập khẩu, xuất khẩu hay loại giao dịch nào khác?",
        "transaction_date": "Giao dịch phát sinh vào ngày hoặc khoảng thời gian nào?",
    },
    "residency": {
        "presence_period": "Bạn cần xác định cư trú cho khoảng thời gian nào và có thông tin ngày đến/ngày đi hoặc số ngày hiện diện tại Việt Nam không?",
        "accommodation": "Trong thời gian đó, cá nhân có nơi ở thường xuyên hoặc chỗ ở thuê tại Việt Nam không? Vui lòng mô tả tình trạng và thời gian sử dụng, không gửi địa chỉ cụ thể.",
        "foreign_residency": "Cá nhân có thông tin hoặc giấy tờ xác nhận cư trú thuế ở nước khác không? Chỉ mô tả tình trạng, không gửi số giấy tờ hay ảnh giấy tờ cá nhân.",
    },
}


def detect_scenario(question, explicit=None):
    if explicit is not None:
        if explicit not in QUESTIONS:
            raise ValueError("unknown clarification scenario")
        return explicit
    q = unicodedata.normalize("NFC", question).casefold()
    if "cư trú" in q or "residency" in q or "tax resident" in q:
        return "residency"
    if "thuế suất" in q and any(word in q for word in ("hàng", "sản phẩm", "gtgt", "vat")):
        return "goods_rate"
    return None


def clarification_questions(question, scenario=None, case_facts=None):
    scenario = detect_scenario(question, scenario)
    if not scenario:
        return ()
    facts = case_facts or {}
    unknown = {"", "unknown", "không rõ", "chưa biết", "chưa xác định"}
    return tuple(prompt for key, prompt in QUESTIONS[scenario].items()
                 if not isinstance(facts.get(key), str) or facts[key].strip().casefold() in unknown)
