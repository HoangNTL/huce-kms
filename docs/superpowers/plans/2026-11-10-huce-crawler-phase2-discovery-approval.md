# HUCE-KMS Content Crawler (Phase 2: Discovery Engine & Approval Queue) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Discovery Engine and Human-in-the-Loop URL Approval subsystem for HUCE-KMS, enabling automatic extraction of candidate article URLs from listing pages/sitemaps and controlled batch crawling of approved items.

**Architecture:** Implement a modular Discovery subsystem in `api.services.crawler.discovery` and Registry in `api.services.crawler.registry`: Listing Page Extractor (heuristic post-card detection) + Sitemap/RSS Parsers + URL Normalizer & Deduplicator → Review Queue (JSON-based state management: `discovered` → `approved`/`rejected`) → Batch/APPROVED Crawler Mode in `CrawlerCoreEngine` with concurrency limits (`max_concurrency=2`) and session tracking (`data/crawled/sessions/`). Expose functionality through new CLI subcommands (`discover`, `approve`, `crawl --input`).

**Tech Stack:** Python 3.12, BeautifulSoup4, LXML, HTTPX, Pydantic V2, `unittest`.

**Spec:** Unified HUCE-KMS Crawler Architecture (`Hybrid — URL-based Crawling + Discovery + Human Approval`) Sections 3.2, 3.3, 5, and 7.

---

## Global Constraints

- **Python Runtime:** `>= 3.12`.
- **RAG & Phase 1 Integrity:** Do NOT modify existing RAG modules or break Phase 1 DIRECT mode.
- **Controlled Scope:** Discovery depth is restricted to listing pages (depth=1 by default), with hard cap `max_items=50` to prevent accidental crawler traps.
- **Domain Allowlist:** Strictly enforce allowlist on all discovered URLs (`huce.edu.vn` and subdomains).
- **Human Approval Gate:** Discovery must NOT automatically ingest into RAG or trigger full crawl; URLs must transition through an approval state (`approved`).
- **Storage Layout:**
  - Discovery output: `apps/backend/data/crawl-queue/discovered_<timestamp>.json`
  - Approved queue: `apps/backend/data/crawl-queue/approved.json`
  - Sessions: `apps/backend/data/crawled/sessions/<session_id>/`
- **Testing Standard:** All modules must have unit tests runnable via `uv run python -m unittest discover -s tests -p "test_*.py"`.

---

## Review Focus

1. **Crawler Traps & Infinite Pagination:** Listing pages with calendar widgets, infinite loops, or query parameter variations must not loop indefinitely.
2. **Boilerplate vs Article Links:** Extractor must reliably differentiate true article links from site navigation, pagination buttons, author archives, or tag links.
3. **URL Canonicalization:** Different URL representations of the same article (e.g. with `?utm_source=...` or `/` at the end or uppercase) must normalize to identical canonical URLs to prevent duplicate crawling.
4. **Batch Concurrency & Rate Limiting:** Batch crawl must respect `max_concurrency` (default 2) and introduce slight delays between requests to avoid triggering web application firewalls (WAF) or overwhelming university servers.
5. **Partial Batch Failures:** If 1 URL in an approved batch of 10 fails (e.g. 500 error), the remaining 9 must complete successfully and the session report must record the partial outcome.

---

## File Structure

```text
apps/backend/
├── src/api/services/crawler/
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── schemas.py                        # DiscoveredItem, DiscoveryResult, DiscoveryRequest
│   │   ├── url_normalizer.py                 # Canonicalization, query param stripping, allowlist check
│   │   ├── listing_extractor.py              # Extract article cards (title, date, URL, summary)
│   │   ├── sitemap_parser.py                 # Parse XML sitemaps
│   │   ├── rss_parser.py                     # Parse RSS/Atom feeds
│   │   └── engine.py                         # DiscoveryEngine orchestrator
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── schemas.py                        # ReviewQueueItem, ReviewQueueState
│   │   └── review_queue.py                   # File-based approval queue (discovered -> approved/rejected)
│   └── core/
│       └── engine.py                         # Extended with crawl_batch() and session logging
├── tools/crawler/
│   └── cli.py                                # Extended with discover, approve, and crawl --input
├── data/
│   └── crawl-queue/                          # Storage for discovery & approved queue JSON files
└── tests/services/crawler/
    ├── test_url_normalizer.py
    ├── test_listing_extractor.py
    ├── test_feed_parsers.py
    ├── test_discovery_engine.py
    ├── test_review_queue.py
    └── test_batch_crawl.py
```

---

### Task 1: Discovery Schemas & URL Normalizer

**Files:**
- Create: `apps/backend/src/api/services/crawler/discovery/__init__.py`
- Create: `apps/backend/src/api/services/crawler/discovery/schemas.py`
- Create: `apps/backend/src/api/services/crawler/discovery/url_normalizer.py`
- Test: `apps/backend/tests/services/crawler/test_url_normalizer.py`

**Interfaces:**
- Consumes: Raw URL string, base URL
- Produces: `DiscoveredItem(url: str, title: str, published_at: str | None, status: str)`, `UrlNormalizer.normalize(url: str, base_url: str) -> str | None`

- [ ] **Step 1: Write failing test for URL Normalizer & Schemas**

```python
# apps/backend/tests/services/crawler/test_url_normalizer.py
import unittest
from api.services.crawler.discovery.url_normalizer import UrlNormalizer
from api.services.crawler.discovery.schemas import DiscoveredItem, DiscoveryResult

class TestUrlNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = UrlNormalizer(allowed_domains=["huce.edu.vn"])

    def test_normalize_valid_relative_url(self):
        res = self.normalizer.normalize("/quy-che-1", base_url="https://ctsv.huce.edu.vn/danh-muc")
        self.assertEqual(res, "https://ctsv.huce.edu.vn/quy-che-1")

    def test_strips_tracking_params_and_fragments(self):
        url = "https://ctsv.huce.edu.vn/thong-bao?utm_source=fb&utm_medium=cpc#section-2"
        res = self.normalizer.normalize(url)
        self.assertEqual(res, "https://ctsv.huce.edu.vn/thong-bao")

    def test_blocks_external_domain(self):
        res = self.normalizer.normalize("https://google.com/search")
        self.assertIsNone(res)

    def test_discovered_item_schema(self):
        item = DiscoveredItem(
            url="https://ctsv.huce.edu.vn/thong-bao-1",
            title="Thông báo học phần",
            published_at="2026-11-10",
        )
        self.assertEqual(item.status, "discovered")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_url_normalizer.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `discovery/schemas.py` and `url_normalizer.py`**

- In `discovery/schemas.py`: Define `DiscoveredItem`, `DiscoveryResult` (with `source_url`, `total_discovered`, `items`, `discovered_at`).
- In `url_normalizer.py`: Implement `normalize(url: str, base_url: str | None = None) -> str | None`:
  - resolve relative URLs via `urljoin(base_url, url)`.
  - strip fragment `#...`.
  - filter out tracking query parameters (`utm_*`, `fbclid`, `gclid`).
  - strip trailing slashes (except root `/`).
  - check domain against `allowed_domains`; if external, return `None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_url_normalizer.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/discovery/ apps/backend/tests/services/crawler/test_url_normalizer.py
git commit -m "feat(crawler): implement discovery schemas and URL normalizer"
```

---

### Task 2: Listing Page Link & Article Extractor

**Files:**
- Create: `apps/backend/src/api/services/crawler/discovery/listing_extractor.py`
- Test: `apps/backend/tests/services/crawler/test_listing_extractor.py`

**Interfaces:**
- Consumes: Raw HTML string, base listing URL
- Produces: `list[DiscoveredItem]`

- [ ] **Step 1: Write failing test for `ListingExtractor`**

```python
# apps/backend/tests/services/crawler/test_listing_extractor.py
import unittest
from api.services.crawler.discovery.listing_extractor import ListingExtractor

SAMPLE_LISTING_HTML = """
<div class="main-content">
    <div class="news-list">
        <article class="post-item">
            <h3 class="post-title"><a href="/thong-bao-hoc-bong-2026">Thông báo học bổng kỳ 2</a></h3>
            <span class="post-date">10/11/2026</span>
            <p class="summary">Xét cấp học bổng cho sinh viên đạt điểm xuất sắc...</p>
        </article>
        <article class="post-item">
            <h3 class="post-title"><a href="/quyet-dinh-khen-thuong">Quyết định khen thưởng</a></h3>
            <span class="post-date">08/11/2026</span>
        </article>
    </div>
    <div class="pagination">
        <a href="/danh-muc?page=2">Trang 2</a>
    </div>
    <div class="footer"><a href="/lien-he">Liên hệ</a></div>
</div>
"""

class TestListingExtractor(unittest.TestCase):
    def test_extract_article_items_from_listing(self):
        items = ListingExtractor.extract_items(
            html=SAMPLE_LISTING_HTML,
            base_url="https://ctsv.huce.edu.vn/danh-muc",
        )
        self.assertEqual(len(items), 2)
        urls = [item.url for item in items]
        self.assertIn("https://ctsv.huce.edu.vn/thong-bao-hoc-bong-2026", urls)
        self.assertIn("https://ctsv.huce.edu.vn/quyet-dinh-khen-thuong", urls)
        self.assertEqual(items[0].published_at, "10/11/2026")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_listing_extractor.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `ListingExtractor` in `discovery/listing_extractor.py`**

- Parse HTML with `BeautifulSoup(html, "lxml")`.
- Remove site navigation and footers.
- Detect recurring article containers: `article`, `.post-item`, `.news-item`, `.item-news`, or `h2/h3 a[href]`.
- For each item:
  - Extract URL and resolve using `UrlNormalizer`.
  - Extract title text.
  - Extract date using regex `\d{1,2}[/-]\d{1,2}[/-]\d{4}` from item text or date elements.
  - Ignore non-article links (e.g. links with anchor `#`, `page=`, `category=`, `/tag/`).
  - Return unique `list[DiscoveredItem]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_listing_extractor.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/discovery/listing_extractor.py apps/backend/tests/services/crawler/test_listing_extractor.py
git commit -m "feat(crawler): implement ListingExtractor for university listing pages"
```

---

### Task 3: Sitemap & RSS Feed Parsers

**Files:**
- Create: `apps/backend/src/api/services/crawler/discovery/sitemap_parser.py`
- Create: `apps/backend/src/api/services/crawler/discovery/rss_parser.py`
- Test: `apps/backend/tests/services/crawler/test_feed_parsers.py`

**Interfaces:**
- Consumes: XML content string, base URL
- Produces: `list[DiscoveredItem]`

- [ ] **Step 1: Write failing test for Sitemap & RSS parsers**

```python
# apps/backend/tests/services/crawler/test_feed_parsers.py
import unittest
from api.services.crawler.discovery.sitemap_parser import SitemapParser
from api.services.crawler.discovery.rss_parser import RssParser

SAMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://daotao.huce.edu.vn/tin-tuc-1</loc>
        <lastmod>2026-11-09</lastmod>
    </url>
</urlset>
"""

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Tin tức HUCE</title>
        <item>
            <title>Kế hoạch xét tốt nghiệp</title>
            <link>https://daotao.huce.edu.vn/tot-nghiep-2026</link>
            <pubDate>Mon, 10 Nov 2026 08:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""

class TestFeedParsers(unittest.TestCase):
    def test_parse_sitemap(self):
        items = SitemapParser.parse(SAMPLE_SITEMAP, base_url="https://daotao.huce.edu.vn")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://daotao.huce.edu.vn/tin-tuc-1")
        self.assertEqual(items[0].published_at, "2026-11-09")

    def test_parse_rss(self):
        items = RssParser.parse(SAMPLE_RSS, base_url="https://daotao.huce.edu.vn")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://daotao.huce.edu.vn/tot-nghiep-2026")
        self.assertEqual(items[0].title, "Kế hoạch xét tốt nghiệp")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_feed_parsers.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `SitemapParser` and `RssParser`**

- In `sitemap_parser.py`: Parse XML via `lxml.etree` or `BeautifulSoup(xml, "xml")`. Extract `<url><loc>` and `<lastmod>`.
- In `rss_parser.py`: Parse `<channel><item>`. Extract `<title>`, `<link>`, and `<pubDate>`. Normalize dates and URLs.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_feed_parsers.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/discovery/sitemap_parser.py apps/backend/src/api/services/crawler/discovery/rss_parser.py apps/backend/tests/services/crawler/test_feed_parsers.py
git commit -m "feat(crawler): implement SitemapParser and RssParser"
```

---

### Task 4: Discovery Engine Orchestrator

**Files:**
- Create: `apps/backend/src/api/services/crawler/discovery/engine.py`
- Test: `apps/backend/tests/services/crawler/test_discovery_engine.py`

**Interfaces:**
- Consumes: Target URL, max_items (int, default 50)
- Produces: `DiscoveryResult(source_url: str, total_discovered: int, items: list[DiscoveredItem], discovered_at: str)`

- [ ] **Step 1: Write failing test for `DiscoveryEngine`**

```python
# apps/backend/tests/services/crawler/test_discovery_engine.py
import unittest
from unittest.mock import AsyncMock, patch
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.core.fetcher import FetchResponse

class TestDiscoveryEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = DiscoveryEngine(check_dns=False)

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    async def test_discover_from_listing_page(self, mock_fetch):
        mock_html = """
        <html><body>
            <div class="post-item"><h3><a href="/tb-1">Thông báo 1</a></h3></div>
            <div class="post-item"><h3><a href="/tb-2">Thông báo 2</a></h3></div>
        </body></html>
        """
        mock_fetch.return_value = FetchResponse(200, mock_html, "https://ctsv.huce.edu.vn/danh-muc")

        res = await self.engine.discover("https://ctsv.huce.edu.vn/danh-muc", max_items=10)
        self.assertEqual(res.source_url, "https://ctsv.huce.edu.vn/danh-muc")
        self.assertEqual(res.total_discovered, 2)
        self.assertEqual(res.items[0].url, "https://ctsv.huce.edu.vn/tb-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_discovery_engine.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `DiscoveryEngine` in `discovery/engine.py`**

- `async def discover(self, url: str, max_items: int = 50) -> DiscoveryResult`:
  1. Fetch content via `HttpFetcher`.
  2. Inspect content:
     - If XML and `<urlset>`: parse with `SitemapParser`.
     - If XML and `<rss>` or `<feed>`: parse with `RssParser`.
     - Otherwise: parse as HTML listing page via `ListingExtractor`.
  3. Cap at `max_items`.
  4. Return `DiscoveryResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_discovery_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/discovery/engine.py apps/backend/tests/services/crawler/test_discovery_engine.py
git commit -m "feat(crawler): implement DiscoveryEngine orchestrator"
```

---

### Task 5: Review Queue & State Management

**Files:**
- Create: `apps/backend/src/api/services/crawler/registry/__init__.py`
- Create: `apps/backend/src/api/services/crawler/registry/schemas.py`
- Create: `apps/backend/src/api/services/crawler/registry/review_queue.py`
- Test: `apps/backend/tests/services/crawler/test_review_queue.py`

**Interfaces:**
- Consumes: `DiscoveryResult`, file paths
- Produces: `ReviewQueueManager(save_discovered, approve_items, reject_items, load_approved)`

- [ ] **Step 1: Write failing test for `ReviewQueueManager`**

```python
# apps/backend/tests/services/crawler/test_review_queue.py
import unittest
import tempfile
from pathlib import Path
from api.services.crawler.registry.review_queue import ReviewQueueManager
from api.services.crawler.discovery.schemas import DiscoveredItem, DiscoveryResult

class TestReviewQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_mgr = ReviewQueueManager(queue_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_approve_items(self):
        result = DiscoveryResult(
            source_url="https://ctsv.huce.edu.vn/danh-muc",
            total_discovered=2,
            items=[
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-1", title="TB 1"),
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-2", title="TB 2"),
            ],
            discovered_at="2026-11-10T12:00:00Z",
        )
        saved_file = self.queue_mgr.save_discovered(result)
        self.assertTrue(saved_file.exists())

        # Approve item 1 only
        approved_file = self.queue_mgr.approve_items(
            discovered_file=saved_file,
            approved_urls=["https://ctsv.huce.edu.vn/tb-1"],
        )
        self.assertTrue(approved_file.exists())
        approved_urls = self.queue_mgr.load_approved_urls(approved_file)
        self.assertEqual(approved_urls, ["https://ctsv.huce.edu.vn/tb-1"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_review_queue.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `ReviewQueueManager` in `registry/review_queue.py`**

- In `registry/schemas.py`: Define `ReviewItemStatus(discovered, approved, rejected, crawled)`.
- In `review_queue.py`:
  - `save_discovered(result: DiscoveryResult, filename: str | None = None) -> Path`: write JSON to `data/crawl-queue/discovered_<timestamp>.json`.
  - `approve_items(discovered_file: Path, approved_urls: list[str] | None = None, approve_all: bool = False, output_file: Path | None = None) -> Path`: produce `approved.json` containing only approved URLs.
  - `load_approved_urls(approved_file: Path) -> list[str]`: parse approved list.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_review_queue.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/registry/ apps/backend/tests/services/crawler/test_review_queue.py
git commit -m "feat(crawler): implement ReviewQueueManager for human-in-the-loop URL approval"
```

---

### Task 6: Batch / APPROVED Crawl Mode in Core Engine

**Files:**
- Modify: `apps/backend/src/api/services/crawler/core/engine.py`
- Modify: `apps/backend/src/api/services/crawler/schemas.py`
- Test: `apps/backend/tests/services/crawler/test_batch_crawl.py`

**Interfaces:**
- Consumes: List of URLs, max_concurrency (int, default 2), session_id
- Produces: `BatchCrawlResult(session_id: str, total_urls: int, successful: int, failed: int, results: list[CrawlResult])`

- [ ] **Step 1: Write failing test for `crawl_batch`**

```python
# apps/backend/tests/services/crawler/test_batch_crawl.py
import unittest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.core.fetcher import FetchResponse

class TestBatchCrawl(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = CrawlerCoreEngine(base_data_dir=Path(self.temp_dir.name), check_dns=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    async def test_batch_crawl_multiple_urls(self, mock_fetch):
        mock_fetch.return_value = FetchResponse(200, "<html><body><main><h1>Item</h1><p>Text</p></main></body></html>", "https://ctsv.huce.edu.vn/item")

        urls = [
            "https://ctsv.huce.edu.vn/item-1",
            "https://ctsv.huce.edu.vn/item-2",
        ]
        batch_res = await self.engine.crawl_batch(urls, max_concurrency=2, skip_media=True)
        self.assertEqual(batch_res.total_urls, 2)
        self.assertEqual(batch_res.successful, 2)
        self.assertEqual(batch_res.failed, 0)
        self.assertTrue((Path(self.temp_dir.name) / "sessions" / batch_res.session_id / "session.json").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_batch_crawl.py`
Expected: FAIL with `AttributeError: 'CrawlerCoreEngine' object has no attribute 'crawl_batch'`.

- [ ] **Step 3: Implement `crawl_batch` in `core/engine.py` and `BatchCrawlResult` in `schemas.py`**

- In `schemas.py`: Define `BatchCrawlResult`.
- In `core/engine.py`:
  - `async def crawl_batch(self, urls: list[str], max_concurrency: int = 2, skip_media: bool = False, session_id: str | None = None) -> BatchCrawlResult`:
    - Generate `session_id = session_id or datetime.now().strftime("%Y-%m-%d_%H%M%S")`.
    - Use `asyncio.Semaphore(max_concurrency)` to bound parallel execution.
    - Collect `results: list[CrawlResult]`.
    - Call `self.storage.save_session(session_id, session_summary, item_results)`.
    - Return `BatchCrawlResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_batch_crawl.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/api/services/crawler/core/engine.py apps/backend/src/api/services/crawler/schemas.py apps/backend/tests/services/crawler/test_batch_crawl.py
git commit -m "feat(crawler): add crawl_batch with concurrency limiting and session storage"
```

---

### Task 7: CLI Subcommands for DISCOVERY & APPROVED Mode

**Files:**
- Modify: `apps/backend/tools/crawler/cli.py`
- Test: `apps/backend/tests/services/crawler/test_cli_discovery.py`

**Interfaces:**
- CLI commands:
  - `uv run python -m tools.crawler.cli discover --url <url> [--max-items 50] [--output <file>]`
  - `uv run python -m tools.crawler.cli approve --input <discovered_json> [--all | --indices 1,2] [--output <approved_json>]`
  - `uv run python -m tools.crawler.cli crawl --input <approved_json> [--max-concurrency 2]`

- [ ] **Step 1: Write failing test for new CLI subcommands**

```python
# apps/backend/tests/services/crawler/test_cli_discovery.py
import unittest
from tools.crawler.cli import build_parser

class TestCLIDiscovery(unittest.TestCase):
    def test_discover_subcommand_args(self):
        parser = build_parser()
        args = parser.parse_args(["discover", "--url", "https://ctsv.huce.edu.vn/quy-che", "--max-items", "20"])
        self.assertEqual(args.command, "discover")
        self.assertEqual(args.url, "https://ctsv.huce.edu.vn/quy-che")
        self.assertEqual(args.max_items, 20)

    def test_approve_subcommand_args(self):
        parser = build_parser()
        args = parser.parse_args(["approve", "--input", "data/crawl-queue/discovered.json", "--all"])
        self.assertEqual(args.command, "approve")
        self.assertTrue(args.all)

    def test_crawl_subcommand_with_input_file(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "--input", "data/crawl-queue/approved.json", "--concurrency", "3"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(str(args.input), "data/crawl-queue/approved.json")
        self.assertEqual(args.concurrency, 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests/services/crawler/test_cli_discovery.py`
Expected: FAIL.

- [ ] **Step 3: Implement CLI updates in `tools/crawler/cli.py`**

- Add `discover` subparser.
- Add `approve` subparser.
- Update `crawl` subparser to accept either `--url` OR `--input` (mutually exclusive group or conditional validation).
- Implement `run_discover` and `run_approve` handlers.
- When `crawl --input` is used: call `engine.crawl_batch(...)` and print batch summary.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests/services/crawler/test_cli_discovery.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/tools/crawler/cli.py apps/backend/tests/services/crawler/test_cli_discovery.py
git commit -m "feat(crawler): add discover and approve commands to CLI runner"
```

---

### Task 8: End-to-End Real-World Verification on HUCE Listing Portals

**Files:**
- Execute Discovery on live `https://ctsv.huce.edu.vn/quy-che-quy-dinh`
- Approve 2 discovered URLs into `data/crawl-queue/approved.json`
- Execute batch crawl on `approved.json`
- Documentation: Create report `docs/analysis/crawler-phase2-verification-report.md`

- [ ] **Step 1: Run `discover` on live CTSV quy-che listing page**

```bash
uv run python -m tools.crawler.cli discover --url "https://ctsv.huce.edu.vn/quy-che-quy-dinh" --max-items 10
```
Verify discovered URLs are extracted, normalized, and saved to `data/crawl-queue/`.

- [ ] **Step 2: Run `approve` on the discovered file**

```bash
uv run python -m tools.crawler.cli approve --input <discovered_file> --indices 1,2
```
Verify `approved.json` contains exactly the selected 2 URLs.

- [ ] **Step 3: Run batch `crawl --input` on approved file**

```bash
uv run python -m tools.crawler.cli crawl --input data/crawl-queue/approved.json
```
Verify both pages are crawled, PDFs & Markdown are generated, and a session record is saved in `data/crawled/sessions/`.

- [ ] **Step 4: Write verification report & commit**

Document live test outcomes in `docs/analysis/crawler-phase2-verification-report.md`.

```bash
git add docs/analysis/crawler-phase2-verification-report.md
git commit -m "docs(crawler): add Phase 2 verification report with live HUCE discovery and approval"
```

---

## Execution Approach Selection

Plan complete and saved to `docs/superpowers/plans/2026-11-10-huce-crawler-phase2-discovery-approval.md`.
Please review the plan. Which execution approach would you prefer?

- **Native (Khuyến nghị)** - Triển khai trực tiếp lần lượt từng task trong phiên làm việc này theo quy trình TDD, nhanh và tối ưu chi phí ngữ cảnh.
- **Subagent-driven** - Phân phối từng task cho các subagent độc lập và review chéo từng task.
