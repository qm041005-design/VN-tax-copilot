
from ai_engine.retrieval.bm25 import BM25Retriever


def run_bm25_retrieval(benchmark, passages):
    retriever = BM25Retriever(passages)
    retrieval_results = []

    for case in benchmark["cases"]:
        if case["answerability"] != "answerable":
            continue

        hits = retriever.search(case["question"], limit=10)

        retrieval_results.append({
            "case_id": case["case_id"],
            "retrieved_passage_ids": [
                str(hit["passage_id"])
                for hit in hits
            ]
        })

    return retrieval_results
