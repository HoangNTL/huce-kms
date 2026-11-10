import unittest
from pathlib import Path
import tempfile
import httpx
from api.services.crawler.core.file_downloader import FileDownloader, DownloadedFileResult
from api.services.crawler.exceptions import MediaDownloadException


class TestFileDownloader(unittest.TestCase):
    def test_file_signature_validation(self):
        valid_pdf_bytes = b"%PDF-1.5 fake pdf content here"
        self.assertTrue(FileDownloader.validate_signature(valid_pdf_bytes, "pdf"))

        invalid_pdf_bytes = b"<html>Not a pdf</html>"
        self.assertFalse(FileDownloader.validate_signature(invalid_pdf_bytes, "pdf"))

        png_bytes = b"\x89PNG\r\n\x1a\n"
        self.assertTrue(FileDownloader.validate_signature(png_bytes, "image"))

    def test_sanitize_filename(self):
        dirty = "../../etc/passwd/Quyet_dinh 123 (HN).pdf"
        clean = FileDownloader.sanitize_filename(dirty, default_stem="document", default_ext=".pdf")
        self.assertEqual(clean, "Quyet_dinh_123_HN.pdf")

    def test_sanitize_filename_fallback_when_empty(self):
        clean = FileDownloader.sanitize_filename("???", default_stem="attachment", default_ext=".pdf")
        self.assertEqual(clean, "attachment.pdf")
