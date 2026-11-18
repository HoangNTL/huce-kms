import unittest
import httpx
from api.services.crawler.core.fetcher import HttpFetcher
from api.services.crawler.exceptions import SSRFBlockedException, FetchException


class TestHttpFetcher(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fetcher = HttpFetcher(allowed_domains=["huce.edu.vn"], check_dns=False)

    def test_blocks_disallowed_domain(self):
        with self.assertRaises(SSRFBlockedException):
            self.fetcher.validate_url("https://malicious-site.com/hack")

    def test_blocks_localhost_and_private_ip(self):
        for bad_url in [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://169.254.169.254",
        ]:
            with self.subTest(url=bad_url):
                with self.assertRaises(SSRFBlockedException):
                    self.fetcher.validate_url(bad_url)

    def test_allows_valid_huce_subdomain(self):
        self.assertTrue(self.fetcher.validate_url("https://ctsv.huce.edu.vn/gioi-thieu"))
        self.assertTrue(self.fetcher.validate_url("https://daotao.huce.edu.vn/thong-bao"))
        self.assertTrue(self.fetcher.validate_url("https://huce.edu.vn"))

    async def test_fetch_html_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, html="<html><body><h1>Test</h1></body></html>", request=request)

        fetcher = HttpFetcher(
            allowed_domains=["huce.edu.vn"],
            transport=httpx.MockTransport(handler),
            check_dns=False,
        )
        res = await fetcher.fetch_html("https://huce.edu.vn")
        self.assertEqual(res.status_code, 200)
        self.assertIn("<h1>Test</h1>", res.html)
        self.assertEqual(res.final_url, "https://huce.edu.vn")

    async def test_fetch_html_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, request=request)

        fetcher = HttpFetcher(
            allowed_domains=["huce.edu.vn"],
            transport=httpx.MockTransport(handler),
            check_dns=False,
        )
        with self.assertRaises(FetchException):
            await fetcher.fetch_html("https://huce.edu.vn/missing")

    async def test_redirect_to_private_ip_blocked_before_execution(self):
        called_urls = []

        def handler(request: httpx.Request) -> httpx.Response:
            called_urls.append(str(request.url))
            if str(request.url) == "https://huce.edu.vn/redirect-trap":
                return httpx.Response(302, headers={"Location": "http://127.0.0.1:8000/secret"}, request=request)
            return httpx.Response(200, text="Secret data", request=request)

        fetcher = HttpFetcher(
            allowed_domains=["huce.edu.vn"],
            transport=httpx.MockTransport(handler),
            check_dns=False,
        )

        with self.assertRaises(SSRFBlockedException):
            await fetcher.fetch_html("https://huce.edu.vn/redirect-trap")

        # Crucial security check: 127.0.0.1 must NEVER have been requested!
        self.assertEqual(called_urls, ["https://huce.edu.vn/redirect-trap"])

    async def test_redirect_to_disallowed_domain_blocked(self):
        called_urls = []

        def handler(request: httpx.Request) -> httpx.Response:
            called_urls.append(str(request.url))
            return httpx.Response(302, headers={"Location": "https://attacker.com/pwn"}, request=request)

        fetcher = HttpFetcher(
            allowed_domains=["huce.edu.vn"],
            transport=httpx.MockTransport(handler),
            check_dns=False,
        )

        with self.assertRaises(SSRFBlockedException):
            await fetcher.fetch_html("https://huce.edu.vn/jump")

        self.assertEqual(called_urls, ["https://huce.edu.vn/jump"])

    async def test_safe_redirect_succeeds(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == "https://huce.edu.vn/old-page":
                return httpx.Response(301, headers={"Location": "https://daotao.huce.edu.vn/new-page"}, request=request)
            if str(request.url) == "https://daotao.huce.edu.vn/new-page":
                return httpx.Response(200, html="<html><body>Final page</body></html>", request=request)
            return httpx.Response(404, request=request)

        fetcher = HttpFetcher(
            allowed_domains=["huce.edu.vn"],
            transport=httpx.MockTransport(handler),
            check_dns=False,
        )

        res = await fetcher.fetch_html("https://huce.edu.vn/old-page")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Final page", res.html)
        self.assertEqual(res.final_url, "https://daotao.huce.edu.vn/new-page")
