import json
from data_pipeline.parser.chunker import chunk_legal_document
from data_pipeline.registry.hierarchy import get_hierarchy_level

doc_code = "Luật số 38/2019/QH14"
doc_type = "Luật"

sample_text = """
Điều 16. Quyền của người nộp thuế
1. Được hướng dẫn giải thích khi có yêu cầu; cung cấp thông tin để thực hiện nghĩa vụ về thuế.
2. Được nhận văn bản liên quan đến kiểm tra thuế bao gồm:
a) Quyết định kiểm tra thuế;
b) Biên bản kiểm tra thuế.
Điều 17. Trách nhiệm của người nộp thuế
1. Đăng ký thuế, sử dụng mã số thuế theo đúng quy định.
"""

level = get_hierarchy_level(doc_type)
results = chunk_legal_document(sample_text, doc_code, level)

print(f"--> Bóc tách thành công {len(results)} đoạn trích:")
print(json.dumps(results, ensure_ascii=False, indent=2))