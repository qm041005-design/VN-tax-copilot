import unittest
from unittest.mock import patch, MagicMock

from data_pipeline.ocr.pilot import SOURCES, official, pdf_links, extract


class PilotTests(unittest.TestCase):
    def test_ten_unique_sources(self):
        self.assertEqual(len(SOURCES), 10)
        self.assertEqual(len({s[0] for s in SOURCES}), 10)

    def test_source_allowlist(self):
        self.assertTrue(official('https://datafiles.chinhphu.vn/file.pdf'))
        for bad in ('http://chinhphu.vn/a', 'https://chinhphu.vn.evil.test/a', 'file:///x'):
            self.assertFalse(official(bad))

    def test_attachment_resolution(self):
        self.assertEqual(pdf_links('<a href="/law.PDF">PDF</a>', 'https://chinhphu.vn/page'),
                         ['https://chinhphu.vn/law.PDF'])

    @patch('data_pipeline.ocr.pilot.fitz.open')
    def test_native_page_mapping_and_nfc(self, opened):
        doc = MagicMock()
        doc.__len__.return_value = 2
        doc.__getitem__.return_value.get_text.return_value = 'Nội dung ' * 30
        from pymupdf import Rect
        doc.__getitem__.return_value.rect = Rect(0, 0, 600, 800)
        doc.__getitem__.return_value.get_image_info.return_value = []
        opened.return_value.__enter__.return_value = doc
        total, pages = extract('unused.pdf', 'SRC', max_pages=1)
        self.assertEqual(total, 2)
        self.assertEqual(pages[0]['original_page'], 1)
        self.assertEqual(pages[0]['source_id'], 'SRC')
        self.assertEqual(pages[0]['extraction_method'], 'native_pdf')


if __name__ == '__main__':
    unittest.main()
