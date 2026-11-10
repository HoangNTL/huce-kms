import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup


@dataclass
class DiscoveredLink:
    """Represents a discovered media or attachment link."""

    url: str
    title: str = ""
    media_type: str = "pdf"


@dataclass
class DiscoveredMedia:
    """Grouped collections of discovered PDFs and Images."""

    pdfs: list[DiscoveredLink] = field(default_factory=list)
    images: list[DiscoveredLink] = field(default_factory=list)


class LinkDiscoverer:
    """Identifies and resolves download links for PDFs and relevant content images."""

    PDF_EXT_RE = re.compile(r"\.pdf($|\?|#)", re.IGNORECASE)
    IMAGE_EXT_RE = re.compile(r"\.(png|jpg|jpeg|webp)($|\?|#)", re.IGNORECASE)
    GDRIVE_FILE_RE = re.compile(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", re.IGNORECASE)

    IGNORED_IMG_CLASSES = re.compile(r"(icon|avatar|logo|emoji|badge|rating)", re.IGNORECASE)

    @classmethod
    def is_pdf_url(cls, href: str) -> bool:
        """Check if an href points to a PDF document."""
        if not href:
            return False
        clean_href = href.strip()
        if clean_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False
        return bool(cls.PDF_EXT_RE.search(clean_href))

    @classmethod
    def is_content_image(cls, img_tag) -> bool:
        """Filter out tracking pixels, icons, logos, and base64 images."""
        src = img_tag.get("src", "").strip()
        if not src or src.startswith("data:"):
            return False

        # Filter out SVGs (usually UI icons)
        if ".svg" in src.lower():
            return False

        # Check explicit dimensions
        width = img_tag.get("width")
        height = img_tag.get("height")
        try:
            if width and int(str(width).replace("px", "")) <= 32:
                return False
            if height and int(str(height).replace("px", "")) <= 32:
                return False
        except ValueError:
            pass

        # Check classes and alt text
        classes = " ".join(img_tag.get("class", []))
        if cls.IGNORED_IMG_CLASSES.search(classes):
            return False

        return True

    @classmethod
    def discover(cls, soup: BeautifulSoup, base_url: str) -> DiscoveredMedia:
        """Scan content DOM and return resolved, deduplicated PDFs and images."""
        discovered_pdfs: list[DiscoveredLink] = []
        discovered_images: list[DiscoveredLink] = []

        seen_pdf_urls: set[str] = set()
        seen_img_urls: set[str] = set()

        # 1. Discover PDFs & Document Links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if cls.is_pdf_url(href):
                abs_url = urljoin(base_url, href)
                if abs_url not in seen_pdf_urls:
                    seen_pdf_urls.add(abs_url)
                    link_title = a_tag.get_text(strip=True) or a_tag.get("title", "") or "Tài liệu PDF"
                    discovered_pdfs.append(
                        DiscoveredLink(url=abs_url, title=link_title, media_type="pdf")
                    )
            elif match := cls.GDRIVE_FILE_RE.search(href):
                file_id = match.group(1)
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                if direct_url not in seen_pdf_urls:
                    seen_pdf_urls.add(direct_url)
                    link_title = a_tag.get_text(strip=True) or a_tag.get("title", "") or "Tài liệu đính kèm (Google Drive)"
                    discovered_pdfs.append(
                        DiscoveredLink(url=direct_url, title=link_title, media_type="pdf")
                    )
                a_tag["href"] = direct_url

        # 1b. Discover Google Drive preview iframes and replace with link
        for iframe in soup.find_all("iframe", src=True):
            src = iframe["src"].strip()
            match = cls.GDRIVE_FILE_RE.search(src)
            if match:
                file_id = match.group(1)
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                if direct_url not in seen_pdf_urls:
                    seen_pdf_urls.add(direct_url)
                    discovered_pdfs.append(
                        DiscoveredLink(url=direct_url, title="Tài liệu đính kèm (Google Drive)", media_type="pdf")
                    )
                new_a = soup.new_tag("a", href=direct_url)
                new_a.string = "Tài liệu đính kèm (Google Drive)"
                iframe.replace_with(new_a)

        # 2. Discover Images
        for img_tag in soup.find_all("img"):
            if cls.is_content_image(img_tag):
                src = img_tag.get("src", "").strip()
                abs_url = urljoin(base_url, src)
                if abs_url not in seen_img_urls:
                    seen_img_urls.add(abs_url)
                    alt_text = img_tag.get("alt", "").strip() or img_tag.get("title", "").strip() or "Hình ảnh minh họa"
                    discovered_images.append(
                        DiscoveredLink(url=abs_url, title=alt_text, media_type="image")
                    )

        return DiscoveredMedia(pdfs=discovered_pdfs, images=discovered_images)
