import unittest

from unicodedata import normalize

from ai_engine.retrieval.bm25 import BM25Retriever, query_references


class TestBM25Retriever(unittest.TestCase):
    def setUp(self):
        self.retriever = BM25Retriever([
            dict(passage_id=1, legal_identifier="01/2099/NĐ-CP",
                 text="Hoàn thuế GTGT cho hàng xuất khẩu"),
            dict(passage_id=2, legal_identifier="02/2099/NĐ-CP",
                 text="Hồ sơ đề nghị hoàn thuế GTGT"),
            dict(passage_id=3, legal_identifier="03/2099/TT-BTC",
                 text="Đăng ký sử dụng hóa đơn điện tử"),
        ])

    def test_document_number(self):
        hits = self.retriever.search("02/2099/nđ-cp")
        self.assertEqual([hit["passage_id"] for hit in hits], [2])

    def test_keyword(self):
        hits = self.retriever.search("hóa đơn điện tử")
        self.assertEqual([hit["passage_id"] for hit in hits], [3])

    def test_no_match(self):
        self.assertEqual(self.retriever.search("thuật toán"), [])

    def test_spaced_ascii_identifier_finds_own_metadata_before_cross_references(self):
        passages = [
            dict(passage_id=index, legal_identifier="88/2099/NĐ-CP",
                 text="99 2099 ND CP nội dung nhắc đến văn bản khác") for index in range(1, 15)
        ] + [dict(passage_id=99, legal_identifier="99/2099/NĐ-CP", text="Quy định mẫu để thử tìm kiếm")]
        query = "99 / 2099 / ND - CP"
        self.assertNotIn(99, [hit["passage_id"] for hit in BM25Retriever(passages, use_legal_references=False).search(query)])
        self.assertEqual(BM25Retriever(passages).search(query)[0]["passage_id"], 99)

    def test_structured_anchor_beats_mentions_of_another_article(self):
        passages = [
            dict(passage_id=index, legal_identifier="99/2099/NĐ-CP", article_number=str(index),
                 clause_number="2", point_letter="a", text="Tham chiếu Điều 12b Khoản 1a Điểm đ")
            for index in range(1, 15)
        ] + [dict(passage_id=99, legal_identifier="99/2099/NĐ-CP", article_number="12b",
                  clause_number="1a", point_letter="đ", text="Nội dung tại vị trí cần tìm")]
        passages += [dict(passage_id=100 + index, legal_identifier="77/2099/NĐ-CP",
                          text="Chủ đề khác không chứa tham chiếu cần tìm") for index in range(30)]
        query = normalize("NFD", "Điểm đ Khoản 1a Điều 12b 99/2099/NĐ-CP")
        old = BM25Retriever(passages, use_legal_references=False).search(query)
        new = BM25Retriever(passages).search(query)
        self.assertNotIn(99, [hit["passage_id"] for hit in old])
        self.assertEqual(new[0]["passage_id"], 99)
        self.assertEqual("Nội dung tại vị trí cần tìm", new[0]["text"])

    def test_plain_keywords_keep_the_lexical_order_and_scores(self):
        passages = self.retriever.passages
        self.assertEqual(self.retriever.search("hóa đơn điện tử"),
                         BM25Retriever(passages, use_legal_references=False).search("hóa đơn điện tử"))

    def test_multiple_references_do_not_bind_one_article_to_both_documents(self):
        _, anchors = query_references("So sánh Điều 2 của 48/2024/QH15 và 67/2025/QH15")
        self.assertEqual(anchors, {})
        _, anchors = query_references("Khoản 1 Điều 1 và Điều 2 của 48/2024/QH15")
        self.assertEqual(anchors, {})

    def test_identifier_without_year_and_article_match_stay_on_the_cited_document(self):
        retriever = BM25Retriever([
            dict(passage_id=1, legal_identifier="12/TCT-CS", article_number="2", text="nội dung mẫu"),
            dict(passage_id=2, legal_identifier="13/TCT-CS", article_number="2", text="nội dung khác"),
        ])
        hits = retriever.search("Điều 2 12 / TCT - CS")
        self.assertEqual([hit["passage_id"] for hit in hits], [1])

    def test_clause_and_point_do_not_boost_a_passage_from_the_wrong_article(self):
        retriever = BM25Retriever([
            dict(passage_id=1, article_number="2", clause_number="1", point_letter="đ", text="mẫu"),
            dict(passage_id=2, article_number="3", clause_number="1", point_letter="đ", text="mẫu"),
            dict(passage_id=3, article_number="3", clause_number="2", point_letter="a", text="mẫu"),
        ])
        self.assertEqual([hit["passage_id"] for hit in retriever.search("Điểm đ Khoản 1 Điều 3")], [2])

    def test_point_d_and_vietnamese_point_dd_remain_distinct(self):
        passages = [dict(passage_id=letter, legal_identifier="99/2099/NĐ-CP", article_number="1",
                         clause_number="1", point_letter=letter, text="Nội dung mẫu giống nhau")
                    for letter in ("d", "đ")]
        self.assertEqual(BM25Retriever(passages).search("Điểm đ Khoản 1 Điều 1")[0]["passage_id"], "đ")
