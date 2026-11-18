import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx

from api.services.crawler.exceptions import MediaDownloadException

logger = logging.getLogger("huce_kms.crawler.downloader")


@dataclass
class DownloadedFileResult:
    """Outcome of downloading a media attachment."""

    file_name: str
    file_path: Path
    file_size: int
    file_hash: str
    mime_type: str
    status: str = "success"
    error: str | None = None


class FileDownloader:
    """Handles async streaming download, file sanitization, signature validation, and hashing."""

    SIGNATURES = {
        "pdf": [b"%PDF"],
        "image": [
            b"\x89PNG\r\n\x1a\n",  # PNG
            b"\xff\xd8\xff",  # JPEG
            b"GIF87a",  # GIF
            b"GIF89a",
            b"RIFF",  # WEBP
        ],
    }

    @classmethod
    def validate_signature(cls, header_bytes: bytes, media_type: str) -> bool:
        """Verify initial bytes against expected magic file signatures."""
        expected = cls.SIGNATURES.get(media_type.lower(), [])
        if not expected:
            return True
        return any(header_bytes.startswith(sig) for sig in expected)

    @classmethod
    def sanitize_filename(cls, name: str, default_stem: str = "attachment", default_ext: str = "") -> str:
        """Sanitize raw filename, stripping path traversal and invalid characters."""
        clean = unquote(name)
        # Strip directory path
        clean = Path(clean).name

        # Extract extension
        ext_match = re.search(r"(\.[a-zA-Z0-9]+)$", clean)
        ext = ext_match.group(1).lower() if ext_match else default_ext.lower()

        # Clean stem
        stem = re.sub(r"(\.[a-zA-Z0-9]+)$", "", clean)
        stem = re.sub(r"[^\w\s-]", "_", stem)
        stem = re.sub(r"[\s_]+", "_", stem).strip("._")

        if not stem:
            stem = default_stem

        if not ext and default_ext:
            ext = default_ext.lower()

        return f"{stem}{ext}"

    @classmethod
    async def download_file_stream(
        cls,
        client: httpx.AsyncClient,
        url: str,
        dest_dir: Path,
        media_type: str,
        max_size_mb: int = 20,
        preferred_name: str | None = None,
        url_validator: Callable[[str], bool] | None = None,
        max_redirects: int = 5,
    ) -> DownloadedFileResult:
        """Stream download a file, enforcing size limits and calculating SHA-256 on the fly with safe redirect checks."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        max_bytes = max_size_mb * 1024 * 1024

        raw_filename = preferred_name or Path(urlsplit(url).path).name or f"file_{media_type}"
        default_ext = ".pdf" if media_type == "pdf" else ".png"
        safe_filename = cls.sanitize_filename(raw_filename, default_stem=f"file_{media_type}", default_ext=default_ext)

        target_path = dest_dir / safe_filename
        # Avoid clashing with existing file in same dir by appending incremental suffix
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        while target_path.exists():
            target_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        hasher = hashlib.sha256()
        total_bytes = 0
        header_checked = False
        mime_type = "application/octet-stream"

        try:
            current_url = url
            stream_ctx = None
            response = None

            for _ in range(max_redirects + 1):
                if url_validator:
                    url_validator(current_url)

                stream_ctx = client.stream("GET", current_url, follow_redirects=False)
                response = await stream_ctx.__aenter__()

                if response.is_redirect:
                    location = response.headers.get("Location")
                    await stream_ctx.__aexit__(None, None, None)
                    stream_ctx = None
                    if not location:
                        raise MediaDownloadException(
                            f"Redirect {response.status_code} missing Location header.",
                            url=current_url,
                        )
                    current_url = str(response.url.join(location))
                    continue

                break
            else:
                if stream_ctx:
                    await stream_ctx.__aexit__(None, None, None)
                raise MediaDownloadException(
                    f"Too many redirects (exceeded limit of {max_redirects}) for '{url}'.",
                    url=url,
                )

            try:
                if response.status_code >= 400:
                    raise MediaDownloadException(
                        f"HTTP {response.status_code} while downloading file.",
                        url=current_url,
                    )

                mime_type = response.headers.get("Content-Type", mime_type).split(";")[0].strip()

                with open(target_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if not chunk:
                            continue

                        if not header_checked:
                            if not cls.validate_signature(chunk[:32], media_type):
                                raise MediaDownloadException(
                                    f"File signature mismatch for expected type '{media_type}'.",
                                    url=current_url,
                                )
                            header_checked = True

                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise MediaDownloadException(
                                f"File size exceeds maximum allowed limit ({max_size_mb}MB).",
                                url=current_url,
                            )

                        hasher.update(chunk)
                        f.write(chunk)
            finally:
                if stream_ctx:
                    await stream_ctx.__aexit__(None, None, None)

            file_hash = f"sha256:{hasher.hexdigest()}"
            return DownloadedFileResult(
                file_name=target_path.name,
                file_path=target_path,
                file_size=total_bytes,
                file_hash=file_hash,
                mime_type=mime_type,
                status="success",
            )

        except Exception as e:
            # Clean up partial file on failure
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception:
                    pass
            logger.warning("Failed to download media '%s': %s", url, e)
            raise
