import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class Deduplicator:
    """Provides canonical URL hashing and content SHA-256 computation."""

    @classmethod
    def canonicalize_url(cls, url: str) -> str:
        """Normalize URL: lowercase scheme & host, strip trailing slash, sort query params."""
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Sort query params
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(query_items))

        # Drop fragment
        return urlunsplit((scheme, netloc, path, sorted_query, ""))

    @classmethod
    def hash_url(cls, url: str) -> str:
        """Return 16-character SHA-256 hex digest of the canonicalized URL."""
        canonical = cls.canonicalize_url(url)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def compute_content_hash(cls, content: str) -> str:
        """Return 'sha256:<digest>' for text content."""
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{h}"
