
import re
from typing import List, Dict, Optional




def combine_context(*parts: str) -> str:

    return " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )



def chunk_legal_document(
    text: str,
    doc_code: str,
    hierarchy_level: int,
    source_page: Optional[int] = None
) -> List[Dict]:

    chunks = []

    if not text or not text.strip():
        return chunks

    

    article_pattern = re.compile(
        r"^[ \t]*Điều[ \t]+(\d+[a-zđ]?)[ \t]*[.:][ \t]*(.*)$",
        re.MULTILINE | re.IGNORECASE
    )

    articles = list(article_pattern.finditer(text))

    
    for i, art_match in enumerate(articles):

        art_num = art_match.group(1).strip()

        art_title = art_match.group(2).strip()

        body_start = art_match.end()

        if i + 1 < len(articles):
            body_end = articles[i + 1].start()
        else:
            body_end = len(text)

        art_body = text[body_start:body_end].strip()

        if not art_body:
            continue

        
        clause_pattern = re.compile(
            r"^[ \t]*(\d+)\.[ \t]+"
            r"(.*?)(?=^[ \t]*\d+\.[ \t]+|\Z)",
            re.MULTILINE | re.DOTALL
        )

        clause_matches = list(
            clause_pattern.finditer(art_body)
        )

        
        if clause_matches:

            # Nội dung mở đầu chung của Điều
            art_intro = art_body[
                :clause_matches[0].start()
            ].strip()

            for cl_match in clause_matches:

                cl_num = int(cl_match.group(1))

                cl_content = cl_match.group(2).strip()

                

                point_pattern = re.compile(
                    r"^[ \t]*([a-zđ])\)[ \t]*"
                    r"(.*?)(?=^[ \t]*[a-zđ]\)[ \t]*|\Z)",
                    re.MULTILINE | re.DOTALL | re.IGNORECASE
                )

                point_matches = list(
                    point_pattern.finditer(cl_content)
                )

                
                if point_matches:

                    # Câu dẫn mở đầu Khoản
                    clause_intro = cl_content[
                        :point_matches[0].start()
                    ].strip()

                    for pt_match in point_matches:

                        pt_letter = pt_match.group(1).lower()

                        pt_content = pt_match.group(2).strip()

                        citation = (
                            f"Điểm {pt_letter}, "
                            f"Khoản {cl_num}, "
                            f"Điều {art_num}, "
                            f"{doc_code}"
                        )

                        # Ghép nội dung mở đầu Điều,
                        # mở đầu Khoản và nội dung Điểm
                        full_text = combine_context(
                            art_intro,
                            clause_intro,
                            pt_content
                        )

                        chunks.append({

                            "article_number": art_num,

                            "article_title": art_title,

                            "clause_number": cl_num,

                            "point_letter": pt_letter,

                            "citation_path": citation,

                            "content": (
                                f"{citation}: {full_text}"
                            ),

                            "source_page": source_page,

                            "hierarchy_level": hierarchy_level
                        })

                
                else:

                    citation = (
                        f"Khoản {cl_num}, "
                        f"Điều {art_num}, "
                        f"{doc_code}"
                    )

                    full_text = combine_context(
                        art_intro,
                        cl_content
                    )

                    chunks.append({

                        "article_number": art_num,

                        "article_title": art_title,

                        "clause_number": cl_num,

                        "point_letter": "",

                        "citation_path": citation,

                        "content": (
                            f"{citation}: {full_text}"
                        ),

                        "source_page": source_page,

                        "hierarchy_level": hierarchy_level
                    })

        

        else:

            point_pattern = re.compile(
                r"^[ \t]*([a-zđ])\)[ \t]*"
                r"(.*?)(?=^[ \t]*[a-zđ]\)[ \t]*|\Z)",
                re.MULTILINE | re.DOTALL | re.IGNORECASE
            )

            point_matches = list(
                point_pattern.finditer(art_body)
            )

            

            if point_matches:

                art_intro = art_body[
                    :point_matches[0].start()
                ].strip()

                for pt_match in point_matches:

                    pt_letter = pt_match.group(1).lower()

                    pt_content = pt_match.group(2).strip()

                    citation = (
                        f"Điểm {pt_letter}, "
                        f"Điều {art_num}, "
                        f"{doc_code}"
                    )

                    full_text = combine_context(
                        art_intro,
                        pt_content
                    )

                    chunks.append({

                        "article_number": art_num,

                        "article_title": art_title,

                        "clause_number": 0,

                        "point_letter": pt_letter,

                        "citation_path": citation,

                        "content": (
                            f"{citation}: {full_text}"
                        ),

                        "source_page": source_page,

                        "hierarchy_level": hierarchy_level
                    })

            

            else:

                citation = (
                    f"Điều {art_num}, {doc_code}"
                )

                chunks.append({

                    "article_number": art_num,

                    "article_title": art_title,

                    "clause_number": 0,

                    "point_letter": "",

                    "citation_path": citation,

                    "content": (
                        f"{citation}: {art_body}"
                    ),

                    "source_page": source_page,

                    "hierarchy_level": hierarchy_level
                })

    return chunks
