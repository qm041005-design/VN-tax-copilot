import json

from data_pipeline.parser.chunker import chunk_legal_document

from data_pipeline.registry.hierarchy import (
    get_hierarchy_level
)



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
"""



level = get_hierarchy_level(doc_type)

results = chunk_legal_document(
    text=sample_text,
    doc_code=doc_code,
    hierarchy_level=level,
    source_page=3
)




assert len(results) == 5, (
    f"LOI: Mong doi 5 doan trich, "
    f"nhung nhan duoc {len(results)}"
)



article_1a = [
    c for c in results
    if c["article_number"] == "1a"
]

assert len(article_1a) == 2, (
    "LOI: Khong tach dung Dieu 1a"
)

assert [
    c["point_letter"] for c in article_1a
] == ["a", "b"], (
    "LOI: Dieu 1a khong co du diem a va b"
)



article_16 = [
    c for c in results
    if c["article_number"] == "16"
]

assert len(article_16) == 3, (
    "LOI: Khong tach dung Dieu 16"
)




for chunk in article_1a:

    assert (
        "Nghị định này quy định chi tiết"
        in chunk["content"]
    ), "LOI: Mat noi dung mo dau Dieu 1a"




article_16_clause_2 = [
    c for c in article_16
    if c["clause_number"] == 2
]

assert len(article_16_clause_2) == 2

for chunk in article_16_clause_2:

    assert (
        "Được nhận văn bản liên quan"
        in chunk["content"]
    ), "LOI: Mat noi dung mo dau Khoan 2"




assert get_hierarchy_level("NGHI_DINH") == 2

assert get_hierarchy_level("Nghị định") == 2

assert get_hierarchy_level("THONG_TU") == 3

assert get_hierarchy_level("LUAT") == 1

assert get_hierarchy_level("CONG_VAN") == 4




try:

    get_hierarchy_level("UNKNOWN")

    raise AssertionError(
        "LOI: UNKNOWN bi chap nhan"
    )

except ValueError:

    pass



for chunk in results:

    assert chunk["source_page"] == 3, (
        "LOI: Sai trang nguon"
    )




for chunk in results:

    assert chunk["citation_path"], (
        "LOI: Thieu citation_path"
    )

    assert doc_code in chunk["citation_path"], (
        "LOI: Sai ma van ban trong citation"
    )




print("\n========== KET QUA KIEM THU ==========")

print("PASS: Nhan dien NGHI_DINH")

print("PASS: UNKNOWN khong bi mac dinh thanh CONG_VAN")

print("PASS: Nhan dien Dieu 1a")

print("PASS: Nhan dien Dieu 16")

print("PASS: Tach du 5 doan trich")

print("PASS: Tach dung diem a, b")

print("PASS: Giu noi dung mo dau Dieu")

print("PASS: Giu noi dung mo dau Khoan")

print("PASS: Luu dung trang nguon")

print("PASS: Tao citation_path")

print("======================================")

print("\nCHI TIET CAC DOAN TRICH:\n")

print(
    json.dumps(
        results,
        ensure_ascii=False,
        indent=2
    )
)
