import json
from datetime import datetime

from data_pipeline.parser.chunker import chunk_legal_document
from data_pipeline.registry.hierarchy import get_hierarchy_level

doc_code = "Nghị định số 126/2020/NĐ-CP"
doc_type = "NGHI_DINH"

sample_text = """
Điều 1a. Phạm vi điều chỉnh bổ sung
Nghị định này quy định chi tiết thi hành một số điều của Luật Quản lý thuế bao gồm:
a) Khai thuế, tính thuế, ấn định thuế;
b) Hoàn thuế, miễn thuế, giảm thuế.

Điều 16. Quyền của người nộp thuế
1. Được hướng dẫn giải thích khi có yêu cầu.
2. Được nhận văn bản liên quan đến việc kiểm tra thuế bao gồm:
a) Quyết định kiểm tra thuế;
b) Biên bản kiểm tra thuế.
2a. Được bổ sung tài liệu giải trình trong thời hạn quy định.
"""

level = get_hierarchy_level(doc_type)

results = chunk_legal_document(
    text=sample_text,
    doc_code=doc_code,
    hierarchy_level=level,
    source_page=3,
)

assert len(results) == 6, (
    f"LOI: Mong doi 6 doan trich, "
    f"nhung nhan duoc {len(results)}"
)

article_1a = [c for c in results if c["article_number"] == "1a"]
assert len(article_1a) == 2, "LOI: Khong tach dung Dieu 1a"
assert [c["point_letter"] for c in article_1a] == ["a", "b"], (
    "LOI: Dieu 1a khong co du diem a va b"
)

article_16 = [c for c in results if c["article_number"] == "16"]
assert len(article_16) == 4, "LOI: Khong tach dung Dieu 16"

for chunk in article_1a:
    assert "Nghị định này quy định chi tiết" in chunk["content"], (
        "LOI: Mat noi dung mo dau Dieu 1a"
    )
    assert chunk["clause_number"] == "0", (
        "LOI: clause_number mac dinh phai la chuoi '0'"
    )

article_16_clause_2 = [c for c in article_16 if c["clause_number"] == "2"]
assert len(article_16_clause_2) == 2, "LOI: Khong tach dung Khoan 2"

for chunk in article_16_clause_2:
    assert "Được nhận văn bản liên quan" in chunk["content"], (
        "LOI: Mat noi dung mo dau Khoan 2"
    )

article_16_clause_2a = [c for c in article_16 if c["clause_number"] == "2a"]
assert len(article_16_clause_2a) == 1, "LOI: Khong giu duoc chu 'a' trong Khoan 2a"

assert get_hierarchy_level("NGHI_DINH") == 2
assert get_hierarchy_level("Nghị định") == 2
assert get_hierarchy_level("THONG_TU") == 3
assert get_hierarchy_level("LUAT") == 1
assert get_hierarchy_level("CONG_VAN") == 4
assert get_hierarchy_level("UNKNOWN") == 5, (
    "LOI: UNKNOWN phai tra ve cap 5 thay vi nem loi"
)

for chunk in results:
    assert chunk["source_page"] == 3, "LOI: Sai trang nguon"
    assert chunk["status"] == "CHUA_XAC_DINH", (
        "LOI: Thieu ngay hieu luc phai mac dinh la CHUA_XAC_DINH"
    )
    assert chunk["citation_path"], "LOI: Thieu citation_path"
    assert doc_code in chunk["citation_path"], (
        "LOI: Sai ma van ban trong citation"
    )

# Kiem tra van ban chua toi ngay hieu luc -> giu CHUA_XAC_DINH
future_chunks = chunk_legal_document(
    text=sample_text,
    doc_code="99/2026/QH15",
    hierarchy_level=1,
    metadata={"effective_date": datetime(2028, 1, 1), "as_of": datetime(2026, 11, 14)},
)
assert all(c["status"] == "CHUA_XAC_DINH" for c in future_chunks), (
    "LOI: Van ban chua toi ngay hieu luc phai giu CHUA_XAC_DINH"
)

# Kiem tra van ban da qua ngay het hieu luc -> HET_HIEU_LUC
expired_chunks = chunk_legal_document(
    text=sample_text,
    doc_code="10/2020/TT-BTC",
    hierarchy_level=3,
    metadata={
        "effective_date": datetime(2020, 1, 1),
        "expiry_date": datetime(2021, 12, 31),
        "as_of": datetime(2026, 11, 14),
    },
)
assert all(c["status"] == "HET_HIEU_LUC" for c in expired_chunks), (
    "LOI: Van ban da qua ngay het han phai gan HET_HIEU_LUC"
)

print("\n========== KET QUA KIEM THU ==========")
print("PASS: Nhan dien NGHI_DINH")
print("PASS: UNKNOWN tra ve cap 5 an toan")
print("PASS: Nhan dien Dieu 1a")
print("PASS: Nhan dien Dieu 16 va Khoan sua doi 2a (dang chuoi)")
print("PASS: Tach du 6 doan trich")
print("PASS: Tach dung diem a, b")
print("PASS: Giu noi dung mo dau Dieu")
print("PASS: Giu noi dung mo dau Khoan")
print("PASS: Mac dinh status = CHUA_XAC_DINH khi thieu ngay hieu luc")
print("PASS: Van ban chua toi ngay hieu luc giu CHUA_XAC_DINH")
print("PASS: Van ban qua han hieu luc gan HET_HIEU_LUC")
print("PASS: Luu dung trang nguon va citation_path")
print("======================================")
print("\nCHI TIET CAC DOAN TRICH:\n")
print(json.dumps(results, ensure_ascii=False, indent=2))