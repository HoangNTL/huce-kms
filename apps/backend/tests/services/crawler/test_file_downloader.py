import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from api.services.crawler.core.file_downloader import DownloadedFileResult, FileDownloader
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

    def test_google_drive_interstitial_confirmation(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as temp_dir:
                dest_dir = Path(temp_dir)
                mock_client = MagicMock()

                interstitial_html = (
                    b"<!DOCTYPE html><html><body>"
                    b'<a href="/uc?export=download&confirm=abc123token&id=fileid">Download anyway</a>'
                    b"</body></html>"
                )
                pdf_bytes = b"%PDF-1.4 valid test pdf content"

                class FakeStreamContext:
                    def __init__(self, content: bytes, content_type: str = "text/html"):
                        self.content = content
                        self.content_type = content_type

                    async def __aenter__(self):
                        resp = MagicMock()
                        resp.is_redirect = False
                        resp.status_code = 200
                        resp.headers = {"Content-Type": self.content_type}

                        async def aiter_bytes(chunk_size=8192):
                            yield self.content

                        resp.aiter_bytes = aiter_bytes

                        async def aread():
                            return b""

                        resp.aread = aread
                        return resp

                    async def __aexit__(self, *args):
                        pass

                def fake_stream(method, url, **kwargs):
                    if "confirm=abc123token" in str(url):
                        return FakeStreamContext(pdf_bytes, "application/pdf")
                    return FakeStreamContext(interstitial_html, "text/html")

                mock_client.stream.side_effect = fake_stream

                result = await FileDownloader.download_file_stream(
                    client=mock_client,
                    url="https://drive.google.com/uc?export=download&id=fileid",
                    dest_dir=dest_dir,
                    media_type="pdf",
                    preferred_name="drive_doc.pdf",
                )

                self.assertEqual(result.status, "success")
                self.assertTrue(result.file_path.exists())
                self.assertEqual(result.file_path.read_bytes(), pdf_bytes)
                all_files = list(dest_dir.glob("*"))
                self.assertEqual(len(all_files), 1)
                self.assertEqual(all_files[0], result.file_path)

        asyncio.run(run_test())

    def test_content_disposition_filename_deduplication(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as temp_dir:
                dest_dir = Path(temp_dir)
                (dest_dir / "report.pdf").write_bytes(b"%PDF-1.4 dummy 0")
                (dest_dir / "report_1.pdf").write_bytes(b"%PDF-1.4 dummy 1")

                mock_client = MagicMock()
                pdf_bytes = b"%PDF-1.4 new pdf content"

                class FakeStreamContext:
                    async def __aenter__(self):
                        resp = MagicMock()
                        resp.is_redirect = False
                        resp.status_code = 200
                        resp.headers = {
                            "Content-Type": "application/pdf",
                            "Content-Disposition": 'attachment; filename="report.pdf"',
                        }

                        async def aiter_bytes(chunk_size=8192):
                            yield pdf_bytes

                        resp.aiter_bytes = aiter_bytes

                        async def aread():
                            return b""

                        resp.aread = aread
                        return resp

                    async def __aexit__(self, *args):
                        pass

                mock_client.stream.return_value = FakeStreamContext()

                result = await FileDownloader.download_file_stream(
                    client=mock_client,
                    url="https://huce.edu.vn/doc.pdf",
                    dest_dir=dest_dir,
                    media_type="pdf",
                    preferred_name="temp.pdf",
                )

                self.assertEqual(result.status, "success")
                self.assertEqual(result.file_name, "report_2.pdf")
                self.assertTrue((dest_dir / "report_2.pdf").exists())

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()



