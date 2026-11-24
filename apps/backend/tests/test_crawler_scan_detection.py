import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter


class TestCrawlerScanDetection(unittest.TestCase):
    def test_landscape_image_is_not_scanned_document(self):
        """Landscape illustrations (e.g. 400x300 or 900x675) should NOT be classified as document scans."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_stat = MagicMock()
        mock_stat.st_size = 150 * 1024  # 150 KB
        mock_path.stat.return_value = mock_stat

        # Mock PyMuPDF returning 900x675 (landscape, aspect ratio = 0.75)
        mock_page = MagicMock()
        mock_page.rect.width = 900.0
        mock_page.rect.height = 675.0

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None

        with patch("pymupdf.open", return_value=mock_doc):
            is_scan = CrawlIngestionAdapter.is_scanned_document_image(mock_path)
            self.assertFalse(is_scan)

    def test_portrait_a4_image_is_scanned_document(self):
        """Portrait A4 sheets (e.g. 476x641, ratio ~ 1.35) should be classified as document scans."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_stat = MagicMock()
        mock_stat.st_size = 200 * 1024  # 200 KB
        mock_path.stat.return_value = mock_stat

        # Mock PyMuPDF returning 476x641 (portrait, aspect ratio = 1.35)
        mock_page = MagicMock()
        mock_page.rect.width = 476.0
        mock_page.rect.height = 641.0

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None

        with patch("pymupdf.open", return_value=mock_doc):
            is_scan = CrawlIngestionAdapter.is_scanned_document_image(mock_path)
            self.assertTrue(is_scan)

    def test_tiny_image_skipped_immediately(self):
        """Images below 40KB are immediately skipped without reading."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_stat = MagicMock()
        mock_stat.st_size = 20 * 1024  # 20 KB
        mock_path.stat.return_value = mock_stat

        is_scan = CrawlIngestionAdapter.is_scanned_document_image(mock_path)
        self.assertFalse(is_scan)


if __name__ == "__main__":
    unittest.main()
