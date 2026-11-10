import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.core.fetcher import FetchResponse
from api.services.crawler.core.file_downloader import DownloadedFileResult

MOCK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Quy chế công tác sinh viên</title></head>
<body>
    <main>
        <h1>Quy chế công tác sinh viên</h1>
        <p>Nội dung quy chế sinh viên chi tiết.</p>
        <a href="https://ctsv.huce.edu.vn/qc.pdf">Tải file PDF</a>
    </main>
</body>
</html>
"""


class TestCrawlerEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = CrawlerCoreEngine(base_data_dir=Path(self.temp_dir.name), check_dns=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    @patch("api.services.crawler.core.file_downloader.FileDownloader.download_file_stream", new_callable=AsyncMock)
    async def test_crawl_page_orchestration(self, mock_download, mock_fetch):
        mock_fetch.return_value = FetchResponse(
            status_code=200,
            html=MOCK_HTML,
            final_url="https://ctsv.huce.edu.vn/quy-che",
        )
        fake_pdf = Path(self.temp_dir.name) / "qc.pdf"
        fake_pdf.write_bytes(b"%PDF-1.5 fake")
        mock_download.return_value = DownloadedFileResult(
            file_name="qc.pdf",
            file_path=fake_pdf,
            file_size=1024,
            file_hash="sha256:dummy",
            mime_type="application/pdf",
            status="success",
        )

        result = await self.engine.crawl_url("https://ctsv.huce.edu.vn/quy-che")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.title, "Quy chế công tác sinh viên")
        self.assertEqual(result.pdf_count, 1)
        self.assertTrue(result.artifact_dir.exists())
        self.assertTrue((result.artifact_dir / "content.md").exists())
        self.assertTrue((result.artifact_dir / "metadata.json").exists())
