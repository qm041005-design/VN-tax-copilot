import re
from typing import List, Dict

def chunk_legal_document(text: str, doc_code: str, hierarchy_level: int) -> List[Dict]:
    chunks = []

    # 1. Tách từng ĐIỀU
    article_pattern = re.compile(
        r'(?:^|\n)Điều\s+(\d+)[\.:]\s*([^\n]+)\n(.*?)(?=(?:\nĐiều\s+\d+[\.:])|\Z)',
        re.DOTALL
    )

    for art_match in article_pattern.finditer(text):
        art_num = int(art_match.group(1))
        art_title = art_match.group(2).strip()
        art_body = art_match.group(3).strip()

        # 2. Tách từng KHOẢN trong Điều
        clause_pattern = re.compile(
            r'(?:^|\n)(\d+)\.\s*(.*?)(?=(?:\n\d+\.\s*)|\Z)',
            re.DOTALL
        )
        clause_matches = list(clause_pattern.finditer(art_body))

        if clause_matches:
            for cl_match in clause_matches:
                cl_num = int(cl_match.group(1))
                cl_content = cl_match.group(2).strip()

                # 3. Tách từng ĐIỂM trong Khoản
                point_pattern = re.compile(
                    r'(?:^|\n)([a-zđ])\)\s*(.*?)(?=(?:\n[a-zđ]\)\s*)|\Z)',
                    re.DOTALL
                )
                point_matches = list(point_pattern.finditer(cl_content))

                if point_matches:
                    for pt_match in point_matches:
                        pt_letter = pt_match.group(1)
                        pt_content = pt_match.group(2).strip()
                        citation = f"Điểm {pt_letter}, Khoản {cl_num}, Điều {art_num}, {doc_code}"
                        chunks.append({
                            "article_number": art_num,
                            "article_title": art_title,
                            "clause_number": cl_num,
                            "point_letter": pt_letter,
                            "citation_path": citation,
                            "content": f"{citation}: {pt_content}",
                            "hierarchy_level": hierarchy_level
                        })
                else:
                    citation = f"Khoản {cl_num}, Điều {art_num}, {doc_code}"
                    chunks.append({
                        "article_number": art_num,
                        "article_title": art_title,
                        "clause_number": cl_num,
                        "point_letter": "",
                        "citation_path": citation,
                        "content": f"{citation}: {cl_content}",
                        "hierarchy_level": hierarchy_level
                    })
        else:
            citation = f"Điều {art_num}, {doc_code}"
            chunks.append({
                "article_number": art_num,
                "article_title": art_title,
                "clause_number": 0,
                "point_letter": "",
                "citation_path": citation,
                "content": f"{citation}: {art_body}",
                "hierarchy_level": hierarchy_level
            })

    return chunks