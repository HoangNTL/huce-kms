import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from api.core.config import settings
from api.services.crawler.exceptions import FetchException, SSRFBlockedException

logger = logging.getLogger("huce_kms.crawler.fetcher")


@dataclass
class FetchResponse:
    """Result of an HTTP HTML fetch operation."""

    status_code: int
    html: str
    final_url: str


class HttpFetcher:
    """Asynchronous HTTP fetcher with SSRF defense and domain allowlist enforcement."""

    def __init__(
        self,
        allowed_domains: list[str] | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        check_dns: bool = True,
    ):
        self.allowed_domains = allowed_domains or settings.CRAWLER_ALLOWED_DOMAINS
        self.timeout = timeout or settings.CRAWLER_REQUEST_TIMEOUT
        self.max_retries = max_retries or settings.CRAWLER_MAX_RETRIES
        self.user_agent = user_agent or settings.CRAWLER_USER_AGENT
        self.transport = transport
        self.check_dns = check_dns

    def validate_url(self, url: str, check_dns: bool | None = None) -> bool:
        """
        Validate URL against domain allowlist and block private/loopback/reserved IPs.
        Raises SSRFBlockedException if validation fails.
        """
        if check_dns is None:
            check_dns = self.check_dns
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            raise SSRFBlockedException(f"Disallowed scheme '{scheme}'. Only HTTP and HTTPS allowed.", url=url)

        hostname = parsed.hostname
        if not hostname:
            raise SSRFBlockedException("URL has no valid hostname.", url=url)

        hostname_lower = hostname.lower()

        # 1. Direct IP check & loopback check
        try:
            direct_ip = ipaddress.ip_address(hostname_lower)
            if direct_ip.is_private or direct_ip.is_loopback or direct_ip.is_reserved or direct_ip.is_link_local:
                raise SSRFBlockedException(f"Direct IP '{direct_ip}' is private or reserved.", url=url)
        except ValueError:
            pass

        if hostname_lower in ("localhost", "localhost.localdomain"):
            raise SSRFBlockedException("Localhost is blocked for security.", url=url)

        # 2. Domain allowlist check
        domain_matched = False
        for allowed in self.allowed_domains:
            allowed_clean = allowed.lower().lstrip(".")
            if hostname_lower == allowed_clean or hostname_lower.endswith(f".{allowed_clean}"):
                domain_matched = True
                break

        if not domain_matched:
            raise SSRFBlockedException(
                f"Domain '{hostname}' is not in allowed domains ({self.allowed_domains}).",
                url=url,
            )

        # 3. DNS Resolution & Private IP check (Anti-SSRF)
        if check_dns:
            try:
                addr_infos = socket.getaddrinfo(hostname_lower, None)
                for addr in addr_infos:
                    ip_str = addr[4][0]
                    ip_obj = ipaddress.ip_address(ip_str)
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local or ip_obj.is_multicast:
                        raise SSRFBlockedException(f"Hostname '{hostname}' resolves to private/reserved IP: {ip_str}", url=url)
            except socket.gaierror as e:
                logger.warning("DNS resolution failed for '%s': %s", hostname, e)

        return True

    async def fetch_html(self, url: str) -> FetchResponse:
        """Fetch page content asynchronously with redirect safety validation and retries."""
        self.validate_url(url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                client_kwargs = {
                    "timeout": httpx.Timeout(self.timeout),
                    "follow_redirects": True,
                    "headers": headers,
                }
                if self.transport is not None:
                    client_kwargs["transport"] = self.transport

                async with httpx.AsyncClient(**client_kwargs) as client:
                    response = await client.get(url)

                    # Validate all intermediate and final redirect URLs
                    for hist in response.history:
                        self.validate_url(str(hist.url))
                    self.validate_url(str(response.url))

                    if response.status_code >= 400:
                        raise FetchException(
                            f"HTTP {response.status_code} error while fetching page.",
                            url=url,
                            status_code=response.status_code,
                        )

                    return FetchResponse(
                        status_code=response.status_code,
                        html=response.text,
                        final_url=str(response.url),
                    )

            except (SSRFBlockedException, FetchException):
                raise
            except Exception as e:
                last_error = e
                logger.warning("Fetch attempt %d failed for '%s': %s", attempt + 1, url, e)
                if attempt == self.max_retries:
                    break

        raise FetchException(f"Failed to fetch '{url}' after {self.max_retries + 1} attempts: {last_error}", url=url)
