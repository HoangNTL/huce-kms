# HUCE-KMS Content Crawler (Phase 1: Base Engine & DIRECT Mode) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the independent, controlled Base Crawler Engine for HUCE-KMS with DIRECT mode CLI execution, extracting clean Markdown from HTML, downloading attached PDFs/images, and producing standardized local Crawl Artifacts.

**Architecture:** Implement a modular, asynchronous crawler pipeline in `api.services.crawler` with strict Separation of Concerns: Safe HTTP Fetcher (with SSRF protection & domain allowlisting) → Main Content Extractor & HTML Cleaner (Trafilatura + BeautifulSoup4) → Media Link Discoverer (PDFs/Images) → Markdown Converter (Markdownify) → Streaming Media Downloader (integrity & SHA-256) → Local Artifact Storage Engine. The system is operated via a standalone CLI tool in `tools/crawler/cli.py` before API or RAG integration.

**Tech Stack:** Python 3.12, FastAPI backend monorepo, `httpx>=0.28`, `beautifulsoup4>=4.12`, `trafilatura>=2.0`, `markdownify>=0.14`, `lxml>=5.2`, Pydantic V2, `unittest`.

**Spec:** Unified HUCE-KMS Crawler Architecture (`Hybrid — URL-based Crawling + Discovery + Human Approval`) provided in User Request on 2026-11-10.

---

## Global Constraints

- **Python Runtime:** `>= 3.12`.
- **Package Manager:** `uv` inside `apps/backend/`.
- **RAG Non-Destructive Rule:** Do NOT modify or refactor existing RAG modules (`DocumentService`, `DocumentParser`, `TextCleaner`, `TextChunker`, `QdrantVectorStore`). The crawler produces independent artifacts.
- **SSRF & Security Rule:** Strict allowlist validation on all URLs and redirect chains; forbid loopback (`127.0.0.1`, `localhost`), link-local (`169.254.0.0/16`), and private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **Domain Allowlist:** Restrict fetch targets to `huce.edu.vn` and its subdomains (`*.huce.edu.vn`).
- **Storage Structure:** Local filesystem storage under `apps/backend/data/crawled/pages/<page_hash>/` and `sessions/<session_id>/`.
- **Output Formats:** Markdown (`content.md`), JSON Metadata (`metadata.json`), downloaded PDFs (`pdfs/`), downloaded Images (`images/`), raw HTML (`raw.html`).
- **Testing Standard:** All modules must have unit tests runnable via `uv run python -m unittest discover tests`.

---

## Review Focus

1. **SSRF and Subdomain Bypasses:** Malicious or malformed URLs (e.g. `http://huce.edu.vn.attacker.com` or private IP redirects) must be strictly rejected before any socket connection.
2. **Partial / Failed Media Downloads:** If a PDF or image link is broken (404/500/timeout), the crawler must log a warning and record the error in `metadata.json` without crashing the entire page crawl job.
3. **MIME & File Signature Spoofing:** Ensure files claiming to be `.pdf` actually match the `%PDF` magic bytes and images match valid signatures, rejecting disguised HTML or executable files.
4. **File Size & Memory Blowup:** Enforce `MAX_FILE_SIZE_MB = 20MB` via streaming chunks; abort streams immediately if size exceeds limit.
5. **Noisy HTML & Non-Standard Layouts:** Older university websites (Drupal, custom PHP, WordPress) lacking standard article tags must gracefully fall back to body-cleaning heuristics without losing the primary text.

---

## File Structure

```text
apps/backend/
├── pyproject.toml                                # Add beautifulsoup4, trafilatura, markdownify, lxml
├── src/api/
│   ├── core/
│   │   └── config.py                             # Add CRAWLER_* settings (allowlist, limits, paths)
│   └── services/
│       └── crawler/
│           ├── __init__.py                       # Package exports
│           ├── exceptions.py                     # Custom Crawler domain exceptions
│           ├── schemas.py                        # Pydantic V2 DTOs (CrawlResult, CrawledMedia, PageMetadata)
│           ├── deduplicator.py                   # URL hashing & SHA-256 deduplication
│           ├── core/
│           │   ├── __init__.py
│           │   ├── fetcher.py                    # Async HTTP client with SSRF & allowlist protection
│           │   ├── extractor.py                  # Title, publish date, metadata extraction
│           │   ├── html_cleaner.py               # Boilerplate removal (Trafilatura + BS4 fallback)
│           │   ├── link_discoverer.py            # Attachment & media link resolution (PDF, images)
│           │   ├── markdown_converter.py         # Clean HTML to Markdown + local link rewrite
│           │   ├── file_downloader.py            # Stream download with hash & magic byte validation
│           │   └── engine.py                     # CrawlerCoreEngine orchestrator
│           └── storage/
│               ├── __init__.py
│               └── artifact_storage.py           # Page & session artifact persistence
├── tools/
│   ├── __init__.py
│   └── crawler/
│       ├── __init__.py
│       └── cli.py                                # CLI Runner for DIRECT mode crawl
├── data/
│   └── crawled/                                  # Local artifact storage directory
└── tests/
    └── services/
        └── crawler/
            ├── __init__.py
            ├── test_fetcher.py
            ├── test_html_cleaner.py
            ├── test_link_discoverer.py
            ├── test_markdown_converter.py
            ├── test_file_downloader.py
            ├── test_artifact_storage.py
            ├── test_crawler_engine.py
            └── test_cli.py
```

---

### Task 1: Dependencies, Configuration, Schemas & Custom Exceptions

**Files:**
- Modify: `apps/backend/pyproject.toml`
- Modify: `apps/backend/src/api/core/config.py`
- Create: `apps/backend/src/api/services/crawler/__init__.py`
- Create: `apps/backend/src/api/services/crawler/exceptions.py`
- Create: `apps/backend/src/api/services/crawler/schemas.py`
- Test: `apps/backend/tests/services/crawler/test_schemas.py`

**Interfaces:**
- Consumes: `api.core.config.Settings`
- Produces: `CrawlerSettings`, `PageMetadata`, `CrawledMediaItem`, `CrawlResult`, `CrawlerException`, `SSRFBlockedException`

- [ ] **Step 1: Write failing test for Crawler Schemas & Configuration**

```python
# apps/backend/tests/services/crawler/test_schemas.py
import unittest
from api.core.config import settings
from api.services.crawler.schemas import CrawlResult, PageMetadata, CrawledMediaItem
from api.services.crawler.exceptions import SSRFBlockedException

class TestCrawlerSchemas(unittest.TestCase):
    def test_settings_has_crawler_defaults(self):
        self.assertIn("huce.edu.vn", settings.CRAWLER_ALLOWED_DOMAINS)
        self.assertEqual(settings.CRAWLER_MAX_FILE_SIZE_MB, 20)

    def test_page_metadata_serialization(self):
        meta = PageMetadata(
            source_url="https://daotao.huce.edu.vn/thong-bao-1",
            canonical_url="https://daotao.huce.edu.vn/thong-bao-1",
            domain="daotao.huce.edu.vn",
            title="Thông báo 1",
            crawled_at="2026-11-10T10:00:00Z",
            content_hash="sha256:abc123",
            markdown_file="content.md",
        )
        data = meta.model_dump()
        self.assertEqual(data["source_url"], "https://daotao.huce.edu.vn/thong-bao-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_schemas.py`
Expected: FAIL with `ModuleNotFoundError` or missing attributes.

- [ ] **Step 3: Add dependencies to `pyproject.toml` and implement config, exceptions & schemas**

Add packages: `beautifulsoup4>=4.12.0`, `trafilatura>=2.0.0`, `markdownify>=0.14.0`, `lxml>=5.2.0`.
Run `uv sync` to update `uv.lock`.
Update `api/core/config.py` with:
- `CRAWLER_DATA_DIR: Path = BACKEND_DIR / "data" / "crawled"`
- `CRAWLER_ALLOWED_DOMAINS: list[str] = ["huce.edu.vn"]`
- `CRAWLER_REQUEST_TIMEOUT: int = 15`
- `CRAWLER_MAX_RETRIES: int = 2`
- `CRAWLER_MAX_FILE_SIZE_MB: int = 20`
- `CRAWLER_USER_AGENT: str = "HUCE-KMS-Crawler/1.0 (+https://huce.edu.vn)"`
Implement `exceptions.py` and `schemas.py` (`PageMetadata`, `CrawledMediaItem`, `CrawlResult`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_schemas.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/pyproject.toml apps/backend/uv.lock apps/backend/src/api/core/config.py apps/backend/src/api/services/crawler/
git commit -m "feat(crawler): add dependencies, schemas, config and exceptions"
```

---

### Task 2: Safe Async HTTP Fetcher with SSRF Protection

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/__init__.py`
- Create: `apps/backend/src/api/services/crawler/core/fetcher.py`
- Test: `apps/backend/tests/services/crawler/test_fetcher.py`

**Interfaces:**
- Consumes: `api.core.config.settings`, `api.services.crawler.exceptions.SSRFBlockedException`
- Produces: `HttpFetcher.fetch_html(url: str) -> FetchResponse(status_code: int, html: str, final_url: str)`

- [ ] **Step 1: Write failing test for `HttpFetcher`**

```python
# apps/backend/tests/services/crawler/test_fetcher.py
import unittest
from api.services.crawler.core.fetcher import HttpFetcher
from api.services.crawler.exceptions import SSRFBlockedException

class TestHttpFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = HttpFetcher(allowed_domains=["huce.edu.vn"])

    def test_blocks_disallowed_domain(self):
        with self.assertRaises(SSRFBlockedException):
            self.fetcher.validate_url("https://malicious-site.com/hack")

    def test_blocks_localhost_and_private_ip(self):
        for bad_url in [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://192.168.1.1",
            "http://10.0.0.1",
        ]:
            with self.subTest(url=bad_url):
                with self.assertRaises(SSRFBlockedException):
                    self.fetcher.validate_url(bad_url)

    def test_allows_valid_huce_subdomain(self):
        self.assertTrue(self.fetcher.validate_url("https://ctsv.huce.edu.vn/gioi-thieu"))
        self.assertTrue(self.fetcher.validate_url("https://daotao.huce.edu.vn/thong-bao"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_fetcher.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `HttpFetcher` in `api/services/crawler/core/fetcher.py`**

Implement URL validation logic:
- Parse `urlsplit(url)`.
- Enforce scheme `http` or `https`.
- Validate domain against `allowed_domains` (exact match or `*.huce.edu.vn`).
- Resolve hostname to IP using `socket.getaddrinfo`, verify IP is not `is_private`, `is_loopback`, `is_reserved`, or `is_link_local` using `ipaddress.ip_address`.
- Implement `fetch_html(url: str) -> tuple[int, str, str]` using `httpx.AsyncClient` with custom timeout, follow_redirects=True, and validate redirect hops.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_fetcher.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/fetcher.py apps/backend/tests/services/crawler/test_fetcher.py
git commit -m "feat(crawler): add HttpFetcher with SSRF and domain allowlist validation"
```

---

### Task 3: HTML Cleaner & Metadata Extractor

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/html_cleaner.py`
- Create: `apps/backend/src/api/services/crawler/core/extractor.py`
- Test: `apps/backend/tests/services/crawler/test_html_cleaner.py`

**Interfaces:**
- Consumes: Raw HTML string, URL
- Produces:
  - `HtmlExtractor.extract_metadata(html: str, url: str) -> ExtractedMeta(title: str, published_at: str | None)`
  - `HtmlCleaner.clean_and_isolate_content(html: str, url: str) -> CleanedHtmlResult(main_content_html: str, soup: BeautifulSoup)`

- [ ] **Step 1: Write failing test for `HtmlCleaner` & `HtmlExtractor`**

```python
# apps/backend/tests/services/crawler/test_html_cleaner.py
import unittest
from api.services.crawler.core.html_cleaner import HtmlCleaner
from api.services.crawler.core.extractor import HtmlExtractor

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Quy chế tuyển sinh 2026 - HUCE</title>
    <meta property="article:published_time" content="2026-03-15T08:00:00Z" />
</head>
<body>
    <header><nav><a href="/">Trang chủ</a><a href="/tin-tuc">Tin tức</a></nav></header>
    <aside class="sidebar"><div class="widget">Banner quảng cáo tuyển sinh</div></aside>
    <main id="main-content" class="entry-content">
        <h1>Quy chế tuyển sinh 2026</h1>
        <p>Chi tiết về kế hoạch và điều kiện xét tuyển đại học chính quy năm 2026.</p>
        <div class="attachments">
            <a href="/uploads/quy-che-2026.pdf">Tải file PDF Quy chế</a>
        </div>
    </main>
    <footer><p>Bản quyền thuộc ĐH Xây Dựng Hà Nội</p></footer>
    <script>console.log("analytics");</script>
</body>
</html>
"""

class TestHtmlCleaningAndExtraction(unittest.TestCase):
    def test_extract_metadata(self):
        meta = HtmlExtractor.extract_metadata(SAMPLE_HTML, "https://tuyensinh.huce.edu.vn/post-1")
        self.assertIn("Quy chế tuyển sinh 2026", meta.title)
        self.assertEqual(meta.published_at, "2026-03-15T08:00:00Z")

    def test_clean_removes_nav_sidebar_footer(self):
        cleaned = HtmlCleaner.clean_and_isolate_content(SAMPLE_HTML, "https://tuyensinh.huce.edu.vn/post-1")
        self.assertNotIn("Banner quảng cáo", cleaned.main_content_html)
        self.assertNotIn("Bản quyền thuộc", cleaned.main_content_html)
        self.assertNotIn("analytics", cleaned.main_content_html)
        self.assertIn("Chi tiết về kế hoạch và điều kiện xét tuyển", cleaned.main_content_html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_html_cleaner.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `HtmlExtractor` and `HtmlCleaner`**

- In `extractor.py`: parse `title` (from `og:title`, `<h1>`, or `<title>`), parse `published_at` (from `article:published_time`, `datePublished`, or common regex in text like `\d{1,2}/\d{1,2}/\d{4}`).
- In `html_cleaner.py`:
  - Use `trafilatura` to extract core text body; if Trafilatura succeeds and retains links, use it.
  - As fallback / DOM-aware cleaner: use `BeautifulSoup(html, "lxml")`, decompose noise tags (`nav`, `header`, `footer`, `aside`, `script`, `style`, `noscript`, `iframe`, `.sidebar`, `.banner`, `.comment`, `.menu`), isolate primary container (`main`, `article`, `.entry-content`, `.post-content`, `#content`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_html_cleaner.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/extractor.py apps/backend/src/api/services/crawler/core/html_cleaner.py apps/backend/tests/services/crawler/test_html_cleaner.py
git commit -m "feat(crawler): implement HtmlExtractor and HtmlCleaner with boilerplate removal"
```

---

### Task 4: Link Discovery for Media & Attachments (PDFs & Images)

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/link_discoverer.py`
- Test: `apps/backend/tests/services/crawler/test_link_discoverer.py`

**Interfaces:**
- Consumes: `BeautifulSoup` instance of main content, base URL
- Produces: `DiscoveredMedia(pdfs: list[DiscoveredLink], images: list[DiscoveredLink])`

- [ ] **Step 1: Write failing test for `LinkDiscoverer`**

```python
# apps/backend/tests/services/crawler/test_link_discoverer.py
import unittest
from bs4 import BeautifulSoup
from api.services.crawler.core.link_discoverer import LinkDiscoverer

HTML_WITH_MEDIA = """
<div class="content">
    <p>Quyết định kèm theo:</p>
    <a href="/files/quyet-dinh.pdf">Tải về Quyết định</a>
    <a href="https://ctsv.huce.edu.vn/docs/phu-luc.PDF">Phụ lục</a>
    <a href="/tin-tuc">Xem tin khác</a>
    <img src="/images/so-do.png" alt="Sơ đồ quy trình" width="600" height="400" />
    <img src="/icons/icon-arrow.svg" alt="icon" width="16" height="16" />
    <img src="data:image/png;base64,iVBORw0KGgoAAA..." alt="tracking" />
</div>
"""

class TestLinkDiscoverer(unittest.TestCase):
    def test_discover_pdfs_and_images(self):
        soup = BeautifulSoup(HTML_WITH_MEDIA, "lxml")
        base_url = "https://ctsv.huce.edu.vn/thong-bao-1"
        discovered = LinkDiscoverer.discover(soup, base_url)

        # Should discover 2 PDFs, resolved to absolute URLs
        pdf_urls = [p.url for p in discovered.pdfs]
        self.assertEqual(len(pdf_urls), 2)
        self.assertIn("https://ctsv.huce.edu.vn/files/quyet-dinh.pdf", pdf_urls)
        self.assertIn("https://ctsv.huce.edu.vn/docs/phu-luc.PDF", pdf_urls)

        # Should discover genuine content image, filtering out icons and base64
        image_urls = [img.url for img in discovered.images]
        self.assertEqual(len(image_urls), 1)
        self.assertIn("https://ctsv.huce.edu.vn/images/so-do.png", image_urls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_link_discoverer.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `LinkDiscoverer`**

- In `link_discoverer.py`:
  - Find all `a[href]`: normalize via `urllib.parse.urljoin(base_url, href)`. Detect PDF by `.pdf` or `.PDF` suffix, or query params pointing to PDF download endpoints.
  - Find all `img[src]`: filter out `data:` URIs, `.svg`, icons under 32x32 (or with classes `icon`, `avatar`), and resolve absolute URLs.
  - Deduplicate discovered URLs.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_link_discoverer.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/link_discoverer.py apps/backend/tests/services/crawler/test_link_discoverer.py
git commit -m "feat(crawler): implement LinkDiscoverer for attached PDFs and article images"
```

---

### Task 5: Markdown Converter with Local Media Link Rewriting

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/markdown_converter.py`
- Test: `apps/backend/tests/services/crawler/test_markdown_converter.py`

**Interfaces:**
- Consumes: Cleaned HTML string, URL, title, published_at, mapping of remote media URLs to local relative paths
- Produces: Formatted Markdown string (`content.md`)

- [ ] **Step 1: Write failing test for `MarkdownConverter`**

```python
# apps/backend/tests/services/crawler/test_markdown_converter.py
import unittest
from api.services.crawler.core.markdown_converter import MarkdownConverter

class TestMarkdownConverter(unittest.TestCase):
    def test_convert_html_to_markdown_with_table_and_local_links(self):
        html = """
        <h2>Kế hoạch đào tạo</h2>
        <table>
            <tr><th>Học phần</th><th>Số tín chỉ</th></tr>
            <tr><td>Toán cao cấp</td><td>3</td></tr>
        </table>
        <p><a href="https://ctsv.huce.edu.vn/quyet-dinh.pdf">Xem văn bản gốc</a></p>
        <img src="https://ctsv.huce.edu.vn/so-do.png" alt="Sơ đồ" />
        """
        media_mapping = {
            "https://ctsv.huce.edu.vn/quyet-dinh.pdf": "./pdfs/quyet-dinh.pdf",
            "https://ctsv.huce.edu.vn/so-do.png": "./images/so-do.png",
        }
        md = MarkdownConverter.convert(
            html=html,
            title="Kế hoạch đào tạo 2026",
            source_url="https://ctsv.huce.edu.vn/ke-hoach",
            crawled_at="2026-11-10T10:00:00Z",
            media_mapping=media_mapping,
        )
        self.assertIn("# Kế hoạch đào tạo 2026", md)
        self.assertIn("| Học phần | Số tín chỉ |", md)
        self.assertIn("[Xem văn bản gốc](./pdfs/quyet-dinh.pdf)", md)
        self.assertIn("![Sơ đồ](./images/so-do.png)", md)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_markdown_converter.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `MarkdownConverter`**

- In `markdown_converter.py`:
  - Pre-process DOM to replace `href` and `src` with mapped local relative paths (`./pdfs/...`, `./images/...`).
  - Convert HTML to Markdown using `markdownify.markdownify` with `heading_style="ATX"`, `autolinks=False`.
  - Prefix standardized header:
    ```markdown
    # {title}

    - **Nguồn:** {source_url}
    - **Ngày crawl:** {crawled_at}
    ```
  - Clean up redundant blank lines (collapse `\n{3,}` to `\n\n`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_markdown_converter.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/markdown_converter.py apps/backend/tests/services/crawler/test_markdown_converter.py
git commit -m "feat(crawler): implement MarkdownConverter with table preservation and local media rewrites"
```

---

### Task 6: Streaming Media Downloader with Integrity & Hash Validation

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/file_downloader.py`
- Test: `apps/backend/tests/services/crawler/test_file_downloader.py`

**Interfaces:**
- Consumes: Media URL, target directory `Path`, `HttpFetcher`
- Produces: `DownloadedFileResult(file_name: str, file_path: Path, file_size: int, file_hash: str, mime_type: str, status: str)`

- [ ] **Step 1: Write failing test for `FileDownloader`**

```python
# apps/backend/tests/services/crawler/test_file_downloader.py
import unittest
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, patch
from api.services.crawler.core.file_downloader import FileDownloader

class TestFileDownloader(unittest.TestCase):
    def test_file_signature_validation(self):
        valid_pdf_bytes = b"%PDF-1.5 fake pdf content here"
        self.assertTrue(FileDownloader.validate_signature(valid_pdf_bytes, "pdf"))

        invalid_pdf_bytes = b"<html>Not a pdf</html>"
        self.assertFalse(FileDownloader.validate_signature(invalid_pdf_bytes, "pdf"))

    def test_sanitize_filename(self):
        dirty = "../../etc/passwd/Quyet_dinh 123 (HN).pdf"
        clean = FileDownloader.sanitize_filename(dirty, default_stem="document", extension=".pdf")
        self.assertEqual(clean, "Quyet_dinh_123_HN.pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_file_downloader.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `FileDownloader`**

- In `file_downloader.py`:
  - `sanitize_filename(raw_name: str, default_stem: str, extension: str) -> str`: strip path traversal characters, replace spaces/special chars with underscores, guarantee lowercase extension.
  - `validate_signature(header_bytes: bytes, file_type: str) -> bool`: check `%PDF` for PDF, `\x89PNG` for PNG, `\xff\xd8\xff` for JPEG.
  - `download_file_stream(client: httpx.AsyncClient, url: str, dest_dir: Path, max_size_mb: int) -> DownloadedFileResult`: stream response chunks, calculate SHA-256 on the fly, abort if size exceeds limit, save to disk.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_file_downloader.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/file_downloader.py apps/backend/tests/services/crawler/test_file_downloader.py
git commit -m "feat(crawler): implement FileDownloader with stream hashing, size limits and signature check"
```

---

### Task 7: Artifact Storage Engine & Deduplicator

**Files:**
- Create: `apps/backend/src/api/services/crawler/deduplicator.py`
- Create: `apps/backend/src/api/services/crawler/storage/__init__.py`
- Create: `apps/backend/src/api/services/crawler/storage/artifact_storage.py`
- Test: `apps/backend/tests/services/crawler/test_artifact_storage.py`

**Interfaces:**
- Consumes: Target URL, HTML string, Markdown string, downloaded media lists, metadata
- Produces: Stored directory under `data/crawled/pages/<url_hash>/` containing `content.md`, `metadata.json`, `raw.html`, `pdfs/`, `images/`

- [ ] **Step 1: Write failing test for `ArtifactStorage` & `Deduplicator`**

```python
# apps/backend/tests/services/crawler/test_artifact_storage.py
import unittest
import tempfile
import json
from pathlib import Path
from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.storage.artifact_storage import ArtifactStorage
from api.services.crawler.schemas import PageMetadata

class TestArtifactStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = ArtifactStorage(base_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_url_hash_consistency(self):
        url = "https://ctsv.huce.edu.vn/thong-bao-1"
        h1 = Deduplicator.hash_url(url)
        h2 = Deduplicator.hash_url(url + "/")  # Trailing slash normalization
        self.assertEqual(h1, h2)

    def test_save_page_artifacts(self):
        meta = PageMetadata(
            source_url="https://ctsv.huce.edu.vn/tb-1",
            canonical_url="https://ctsv.huce.edu.vn/tb-1",
            domain="ctsv.huce.edu.vn",
            title="Thông báo 1",
            crawled_at="2026-11-10T10:00:00Z",
            content_hash="sha256:12345",
            markdown_file="content.md",
        )
        page_dir = self.storage.save_page(
            url="https://ctsv.huce.edu.vn/tb-1",
            metadata=meta,
            raw_html="<html><body>test</body></html>",
            markdown_content="# Thông báo 1\nTest",
        )
        self.assertTrue((page_dir / "content.md").exists())
        self.assertTrue((page_dir / "metadata.json").exists())
        self.assertTrue((page_dir / "raw.html").exists())
        self.assertTrue((page_dir / "pdfs").exists())
        self.assertTrue((page_dir / "images").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_artifact_storage.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `Deduplicator` and `ArtifactStorage`**

- In `deduplicator.py`:
  - `hash_url(url: str) -> str`: canonicalize URL (lowercase scheme/host, strip trailing slash, sort query params), return MD5 or first 16 chars of SHA-256 for folder naming.
  - `compute_content_hash(text: str) -> str`: return SHA-256 of text.
- In `artifact_storage.py`:
  - Manage directory structure: `base_dir / "pages" / <url_hash>/`.
  - Atomic writing of `content.md`, `raw.html`, and `metadata.json` (matching schema in Spec Section 5).
  - Create subdirectories `pdfs/` and `images/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_artifact_storage.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/deduplicator.py apps/backend/src/api/services/crawler/storage/ apps/backend/tests/services/crawler/test_artifact_storage.py
git commit -m "feat(crawler): implement ArtifactStorage and Deduplicator for structured local files"
```

---

### Task 8: Crawler Core Engine Orchestrator

**Files:**
- Create: `apps/backend/src/api/services/crawler/core/engine.py`
- Test: `apps/backend/tests/services/crawler/test_crawler_engine.py`

**Interfaces:**
- Consumes: Target URL, optional options (`skip_media: bool`, `session_id: str | None`)
- Produces: `CrawlResult` containing page status, execution time, artifact directory path, discovered and downloaded media counts, and error list

- [ ] **Step 1: Write failing test for `CrawlerCoreEngine`**

```python
# apps/backend/tests/services/crawler/test_crawler_engine.py
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile
from api.services.crawler.core.engine import CrawlerCoreEngine

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

class TestCrawlerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = CrawlerCoreEngine(base_data_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    @patch("api.services.crawler.core.file_downloader.FileDownloader.download_file_stream", new_callable=AsyncMock)
    async def test_crawl_page_orchestration(self, mock_download, mock_fetch):
        mock_fetch.return_value = (200, MOCK_HTML, "https://ctsv.huce.edu.vn/quy-che")
        mock_download.return_value = {
            "file_name": "qc.pdf",
            "file_path": Path(self.temp_dir.name) / "qc.pdf",
            "file_size": 1024,
            "file_hash": "sha256:dummy",
            "mime_type": "application/pdf",
            "status": "success"
        }

        result = await self.engine.crawl_url("https://ctsv.huce.edu.vn/quy-che")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.title, "Quy chế công tác sinh viên")
        self.assertEqual(result.pdf_count, 1)
        self.assertTrue(result.artifact_dir.exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_crawler_engine.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `CrawlerCoreEngine`**

- In `engine.py`:
  - `async def crawl_url(url: str, skip_media: bool = False, session_id: str | None = None) -> CrawlResult`:
    1. Validate URL & Fetch HTML via `HttpFetcher`.
    2. Extract metadata (`title`, `published_at`) via `HtmlExtractor`.
    3. Clean and isolate main content via `HtmlCleaner`.
    4. Discover attachments (PDFs & Images) via `LinkDiscoverer`.
    5. Prepare target page artifact directory via `ArtifactStorage`.
    6. Download media via `FileDownloader` (unless `skip_media=True`), map remote URLs to local relative paths.
    7. Convert HTML to clean Markdown with rewritten local links via `MarkdownConverter`.
    8. Write `content.md`, `metadata.json`, and `raw.html` to disk.
    9. Return populated `CrawlResult`.
    10. Gracefully catch media failures without failing the whole page crawl.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_crawler_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/engine.py apps/backend/tests/services/crawler/test_crawler_engine.py
git commit -m "feat(crawler): implement CrawlerCoreEngine orchestrator"
```

---

### Task 9: CLI Runner for DIRECT Mode (`tools/crawler/cli.py`)

**Files:**
- Create: `apps/backend/tools/__init__.py`
- Create: `apps/backend/tools/crawler/__init__.py`
- Create: `apps/backend/tools/crawler/cli.py`
- Test: `apps/backend/tests/services/crawler/test_cli.py`

**Interfaces:**
- Consumes: Command line arguments (`crawl --url <url> [--output-dir <path>] [--skip-media] [--verbose]`)
- Produces: Terminal feedback with status, execution time, artifact directory, and exit code 0 or 1

- [ ] **Step 1: Write failing test for CLI argument parsing**

```python
# apps/backend/tests/services/crawler/test_cli.py
import unittest
from tools.crawler.cli import build_parser

class TestCrawlerCLI(unittest.TestCase):
    def test_parser_crawl_command(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "--url", "https://ctsv.huce.edu.vn/thong-bao-1", "--skip-media"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.url, "https://ctsv.huce.edu.vn/thong-bao-1")
        self.assertTrue(args.skip_media)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_cli.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `cli.py`**

- In `tools/crawler/cli.py`:
  - Build argparse structure supporting `crawl` (and placeholder for future `discover`).
  - Configure logging format based on `--verbose`.
  - Instantiate `CrawlerCoreEngine`.
  - Run async crawl using `asyncio.run()`.
  - Format output clearly:
    ```text
    ============================================================
    HUCE-KMS CONTENT CRAWLER — DIRECT MODE
    ============================================================
    URL:          https://ctsv.huce.edu.vn/thong-bao-1
    Title:        Thông báo v/v đăng ký học phần...
    Status:       SUCCESS (1.24s)
    Artifact Dir: data/crawled/pages/8f2a1b...
    - Markdown:   data/crawled/pages/8f2a1b.../content.md
    - Metadata:   data/crawled/pages/8f2a1b.../metadata.json
    - PDFs (2):   pdfs/quyet-dinh.pdf, pdfs/phu-luc.pdf
    - Images (1): images/so-do.png
    ============================================================
    ```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/tools/ apps/backend/tests/services/crawler/test_cli.py
git commit -m "feat(crawler): implement CLI runner for DIRECT crawling mode"
```

---

### Task 10: Real-World Verification on Target HUCE Websites

**Files:**
- Execute verification runs from CLI
- Output verified files under `apps/backend/data/crawled/pages/`
- Documentation: Create report `docs/analysis/crawler-phase1-verification-report.md`

**Targets to Test:**
1. A live notification from `https://ctsv.huce.edu.vn/` (e.g. `/quy-che-quy-dinh` or `/bieu-mau` or a specific post containing PDF attachments).
2. A live post from `https://tuyensinh.huce.edu.vn/` (e.g. `/thong-tin-tuyen-sinh-dai-hoc-chinh-quy` containing text + images/PDFs).

- [ ] **Step 1: Run DIRECT crawl on target 1 (CTSV HUCE)**

Run:
```bash
uv run python -m tools.crawler.cli crawl --url "https://ctsv.huce.edu.vn/quy-che-quy-dinh"
```
Verify terminal output and check created directory in `apps/backend/data/crawled/pages/<hash>/`.

- [ ] **Step 2: Inspect generated artifacts for target 1**

- Verify `content.md`: Clean, readable Markdown, headers, tables, links intact, menu/footer removed.
- Verify `metadata.json`: Contains correct URL, title, SHA-256 hashes, media records.
- Verify `pdfs/`: Any linked PDF is downloaded, not corrupted (test opening with PyMuPDF or `pymupdf.open(...)`).
- Verify `images/`: Downloaded images are valid.

- [ ] **Step 3: Run DIRECT crawl on target 2 (Tuyensinh HUCE)**

Run:
```bash
uv run python -m tools.crawler.cli crawl --url "https://tuyensinh.huce.edu.vn/thong-tin-tuyen-sinh-dai-hoc-chinh-quy"
```
Verify terminal output and check created directory in `apps/backend/data/crawled/pages/<hash>/`.

- [ ] **Step 4: Write verification report**

Document the crawled URLs, artifact file paths, file sizes, and sample Markdown snippet in `docs/analysis/crawler-phase1-verification-report.md`.

- [ ] **Step 5: Commit verification report**

```bash
git add docs/analysis/crawler-phase1-verification-report.md
git commit -m "docs(crawler): add Phase 1 base engine verification report with live HUCE tests"
```

---

## Execution Approach Selection

Plan complete and saved to `docs/superpowers/plans/2026-11-10-huce-crawler-base-engine.md`.
Please review the plan. Which execution approach would you prefer?

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end. Runs well with a mid-tier session model, since the plan carries the design.

**For this plan I recommend Native**, because the tasks build directly on sequential components (Fetcher → Cleaner → Discoverer → Downloader → Storage → Engine → CLI) in the same backend package, and native execution allows rapid iterative implementation and testing against the live local python environment. Does the plan capture what you want, and which approach should we use?
