import logging
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from api.core.config import settings

logger = logging.getLogger("huce_kms.crawler.normalizer")


class UrlNormalizer:
    """Canonicalizes, cleans tracking tags, and enforces domain allowlists on URLs."""

    TRACKING_QUERY_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "_ga",
        "ref",
    }

    def __init__(self, allowed_domains: list[str] | None = None):
        self.allowed_domains = allowed_domains or settings.CRAWLER_ALLOWED_DOMAINS

    def is_allowed_domain(self, hostname: str) -> bool:
        """Check if hostname matches or is a subdomain of any allowed domain."""
        if not hostname:
            return False
        hostname_lower = hostname.lower()
        for allowed in self.allowed_domains:
            clean = allowed.lower().lstrip(".")
            if hostname_lower == clean or hostname_lower.endswith(f".{clean}"):
                return True
        return False

    def normalize(self, url: str, base_url: str | None = None) -> str | None:
        """
        Normalize and validate URL:
        1. Resolve relative paths against base_url.
        2. Enforce http/https.
        3. Check allowed domain.
        4. Strip tracking query parameters and fragment.
        5. Return canonical string or None if invalid.
        """
        if not url:
            return None

        clean_url = url.strip()
        if clean_url.startswith(("#", "javascript:", "mailto:", "tel:")):
            return None

        # Resolve relative URL
        if base_url:
            clean_url = urljoin(base_url, clean_url)

        try:
            parsed = urlsplit(clean_url)
        except Exception:
            return None

        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return None

        hostname = parsed.hostname
        if not hostname or not self.is_allowed_domain(hostname):
            return None

        # Normalize path: strip trailing slash unless path is just "/"
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Filter out tracking query params
        filtered_query: list[tuple[str, str]] = []
        if parsed.query:
            for k, v in parse_qsl(parsed.query, keep_blank_values=True):
                if k.lower() not in self.TRACKING_QUERY_PARAMS:
                    filtered_query.append((k, v))

        query_str = urlencode(sorted(filtered_query)) if filtered_query else ""

        # Drop fragment
        return urlunsplit((scheme, hostname.lower(), path, query_str, ""))
