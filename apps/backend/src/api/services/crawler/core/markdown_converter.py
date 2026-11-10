import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from markdownify import markdownify


class MarkdownConverter:
    """Transforms cleaned HTML into readable, standard Markdown with local media link resolution."""

    @classmethod
    def convert(
        cls,
        html: str,
        title: str,
        source_url: str,
        crawled_at: str | None = None,
        published_at: str | None = None,
        media_mapping: dict[str, str] | None = None,
    ) -> str:
        """Convert HTML body to Markdown with standardized header and local media paths."""
        soup = BeautifulSoup(html, "lxml")

        # Rewrite remote links to local relative paths if provided
        if media_mapping:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if href in media_mapping:
                    a_tag["href"] = media_mapping[href]

            for img_tag in soup.find_all("img", src=True):
                src = img_tag["src"].strip()
                if src in media_mapping:
                    img_tag["src"] = media_mapping[src]

        # Convert to Markdown using ATX headers (# H1, ## H2)
        raw_md = markdownify(
            str(soup),
            heading_style="ATX",
            strip=["script", "style"],
            autolinks=False,
        )

        # Clean excess whitespace
        cleaned_body = re.sub(r"\r\n|\r", "\n", raw_md)
        cleaned_body = re.sub(r"\n{3,}", "\n\n", cleaned_body).strip()

        # Build standardized document header
        c_time = crawled_at or datetime.now(timezone.utc).isoformat()
        header_lines = [
            f"# {title.strip()}",
            "",
            f"- **Nguồn:** {source_url}",
            f"- **Ngày crawl:** {c_time}",
        ]
        if published_at:
            header_lines.append(f"- **Ngày đăng:** {published_at}")

        header_lines.extend(["", "---", ""])
        header = "\n".join(header_lines)

        # Avoid repeating the main title if it is the very first heading in body
        first_h1_match = re.match(r"^\s*#\s+(.+)$", cleaned_body, re.MULTILINE)
        if first_h1_match and first_h1_match.group(1).strip().lower() == title.strip().lower():
            cleaned_body = re.sub(r"^\s*#\s+[^\n]+\n*", "", cleaned_body, count=1).strip()

        return f"{header}\n{cleaned_body}".strip()
