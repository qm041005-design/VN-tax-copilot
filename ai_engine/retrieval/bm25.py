import re
from unicodedata import normalize

from rank_bm25 import BM25Okapi

TOKEN_PATTERN = re.compile(r"\w+(?:[./-]\w+)*")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(normalize("NFC", text).casefold())


class BM25Retriever:
    def __init__(self, passages: list[dict]):
        self.passages = [passage.copy() for passage in passages]
        self.tokenized_passages = []
        for passage in self.passages:
            identifier = passage.get("legal_identifier") or ""
            self.tokenized_passages.append(tokenize(f"{identifier} {passage['text']}"))

        self.index = (
            BM25Okapi(self.tokenized_passages) if any(self.tokenized_passages) else None
        )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        query_tokens = tokenize(query)
        if self.index is None or not query_tokens or limit <= 0:
            return []

        query_terms = set(query_tokens)
        scores = self.index.get_scores(query_tokens)
        hits = []
        for passage, tokens, score in zip(self.passages, self.tokenized_passages, scores):
            if query_terms.intersection(tokens):
                hits.append({**passage, "score": float(score)})

        hits.sort(key=lambda hit: hit["score"], reverse=True)
        return hits[:limit]
