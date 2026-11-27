import unittest

from ai_engine.retrieval.bm25 import BM25Retriever


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
