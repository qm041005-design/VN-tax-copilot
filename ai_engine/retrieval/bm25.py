import re
from heapq import nlargest
from unicodedata import combining, normalize

from rank_bm25 import BM25Okapi

TOKEN_PATTERN = re.compile(r"\w+(?:[./-]\w+)*")
IDENTIFIER_PATTERN = re.compile(
    r"(?<!\w)\d+\s*/\s*(?:\d{4}\s*/\s*[^\W\d_]+(?:\s*\d+)?(?:\s*-\s*[^\W_]+)*"
    r"|[^\W\d_]+(?:\s*-\s*[^\W_]+)+)(?!\w)", re.IGNORECASE,
)
ANCHOR_PATTERNS = {
    "article_number": re.compile(r"\b(?:điều|dieu)\s+(\d+[a-zđ]?)\b", re.IGNORECASE),
    "clause_number": re.compile(r"\b(?:khoản|khoan)\s+(\d+[a-zđ]?)\b", re.IGNORECASE),
    "point_letter": re.compile(r"\b(?:điểm|diem)\s+([a-zđ])\b", re.IGNORECASE),
}


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(normalize("NFC", text).casefold())


def canonical_identifier(identifier: str) -> str:
    # Only document identifiers: Vietnamese content and Điểm đ keep their accents.
    text = normalize("NFD", identifier.casefold().replace("đ", "d"))
    return "".join(char for char in text if not char.isspace() and not combining(char))


def query_references(query: str) -> tuple[set[str], dict[str, str]]:
    query = normalize("NFC", query)
    identifiers = {canonical_identifier(match.group()) for match in IDENTIFIER_PATTERN.finditer(query)}
    anchors = {}
    # A query citing multiple instruments does not bind one article to all of them.
    if len(identifiers) <= 1:
        for field, pattern in ANCHOR_PATTERNS.items():
            values = {value.casefold() for value in pattern.findall(query)}
            if len(values) > 1:
                break
            if len(values) == 1:
                anchors[field] = values.pop()
    if not identifiers and "article_number" not in anchors:
        anchors.clear()
    return identifiers, anchors


def matching_anchor_depth(reference: dict[str, str], anchors: dict[str, str]) -> int:
    depth = 0
    for field, value in anchors.items():
        if reference[field] != value:
            break
        depth += 1
    return depth


class BM25Retriever:
    def __init__(self, passages: list[dict], *, use_legal_references: bool = True):
        self.passages = [passage.copy() for passage in passages]
        self.use_legal_references = use_legal_references
        self.references = []
        self.tokenized_passages = []
        for passage in self.passages:
            identifier = passage.get("legal_identifier") or ""
            title = passage.get("article_title") or ""
            self.tokenized_passages.append(tokenize(f"{identifier} {title} {passage['text']}"))
            if use_legal_references:
                reference = {
                    field: normalize("NFC", str(passage.get(field) or "")).strip().casefold()
                    for field in ANCHOR_PATTERNS
                }
                reference["legal_identifier"] = canonical_identifier(identifier)
                self.references.append(reference)

        self.index = (
            BM25Okapi(self.tokenized_passages) if any(self.tokenized_passages) else None
        )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        query_tokens = tokenize(query)
        if self.index is None or not query_tokens or limit <= 0:
            return []

        query_terms = set(query_tokens)
        identifiers, anchors = query_references(query) if self.use_legal_references else (set(), {})
        has_references = bool(identifiers or anchors)
        scores = self.index.get_scores(query_tokens)
        hits = []
        for index, (tokens, score) in enumerate(zip(self.tokenized_passages, scores)):
            document_match = False
            anchor_depth = 0
            if has_references:
                reference = self.references[index]
                document_match = reference["legal_identifier"] in identifiers
                if anchors and (document_match or not identifiers):
                    anchor_depth = matching_anchor_depth(reference, anchors)
            full_anchor_match = bool(anchors) and anchor_depth == len(anchors)
            if document_match or full_anchor_match or query_terms.intersection(tokens):
                hits.append(((document_match, anchor_depth, float(score)), index))

        # Stable ties keep the registry order. The score remains the original BM25
        # score; explicit document/Điều/Khoản/Điểm matches are separate priorities.
        top_hits = nlargest(limit, hits, key=lambda item: item[0])
        return [{**self.passages[index], "score": priority[-1]} for priority, index in top_hits]
