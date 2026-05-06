import io
import ipaddress
import re
import socket
import uuid
from typing import Union
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from ebooklib import epub

# ── constants ────────────────────────────────────────────────────────────────
MAX_IDENTIFIER_LENGTH = 40
MAX_FILENAME_LENGTH = 60
MAX_REDIRECTS = 5

# ── page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="web2ebook", page_icon="📖", layout="centered")

st.title("📖 web2ebook")
st.caption("Convert any web page to an EPUB ebook in one click.")

# ── helpers ──────────────────────────────────────────────────────────────────

def _check_address(addr: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> None:
    """Raise ValueError if the address is restricted."""
    if (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_multicast):
        raise ValueError(
            f"Requests to {addr} are not allowed "
            f"(address is private/loopback/link-local/reserved/multicast)."
        )


def _validate_url(url: str) -> None:
    """Raise ValueError for unsafe or non-HTTP(S) URLs (first-pass SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http/https URLs are supported (got '{parsed.scheme}').")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")
    # If the hostname is already a numeric IP, validate it directly.
    try:
        _check_address(ipaddress.ip_address(hostname))
        return
    except ValueError as exc:
        # Re-raise restriction errors; ignore "not a valid IP" errors from ip_address()
        if "not allowed" in str(exc):
            raise


class _SSRFBlockingAdapter(requests.adapters.HTTPAdapter):
    """HTTPAdapter that resolves + validates the target IP on every send().

    This covers both the initial request and every redirect hop, preventing
    redirect-based SSRF bypasses and reducing the DNS-rebinding window.
    """

    def send(self, request, *args, **kwargs):
        parsed = urlparse(request.url)
        hostname = parsed.hostname
        if hostname:
            try:
                infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except OSError as exc:
                raise ValueError(f"Could not resolve '{hostname}': {exc}") from exc
            for info in infos:
                _check_address(ipaddress.ip_address(info[4][0]))
        return super().send(request, *args, **kwargs)


def _safe_session() -> requests.Session:
    session = requests.Session()
    adapter = _SSRFBlockingAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.max_redirects = MAX_REDIRECTS
    return session


def fetch_page(url: str) -> BeautifulSoup:
    """Download a URL and return its parsed HTML."""
    _validate_url(url)  # Fast first-pass check (scheme + numeric-IP guard)
    headers = {"User-Agent": "Mozilla/5.0 (web2ebook/1.0)"}
    session = _safe_session()
    resp = session.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def extract_content(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (title, body_html) extracted from a parsed page."""
    title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"

    # Remove noisy elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Prefer <article> or <main>, fall back to <body>
    body = soup.find("article") or soup.find("main") or soup.find("body")
    body_html = str(body) if body else "<p>No content found.</p>"

    return title, body_html


def build_epub(title: str, body_html: str, source_url: str) -> bytes:
    """Assemble an EPUB from the extracted content and return it as bytes."""
    book = epub.EpubBook()
    slug = re.sub(r"[^a-z0-9]", "-", title.lower())[:MAX_IDENTIFIER_LENGTH]
    book.set_identifier("web2ebook-" + (slug if slug.strip("-") else str(uuid.uuid4())))
    book.set_title(title)
    book.set_language("en")
    book.add_metadata("DC", "source", source_url)

    # Main chapter
    chapter = epub.EpubHtml(title=title, file_name="content.xhtml", lang="en")
    chapter.content = f"<h1>{title}</h1>\n{body_html}"
    book.add_item(chapter)

    # Navigation
    book.toc = (epub.Link("content.xhtml", title, "content"),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]

    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


# ── UI ───────────────────────────────────────────────────────────────────────

url = st.text_input(
    "Web page URL",
    placeholder="https://example.com/article",
)

if st.button("Convert to EPUB", type="primary", disabled=not url):
    with st.spinner("Fetching and converting…"):
        try:
            soup = fetch_page(url)
            title, body_html = extract_content(soup)
            epub_bytes = build_epub(title, body_html, url)

            safe_name = re.sub(r"[^\w\-]", "_", title)[:MAX_FILENAME_LENGTH] or "ebook"
            st.success(f"✅ Converted: **{title}**")
            st.download_button(
                label="⬇️ Download EPUB",
                data=epub_bytes,
                file_name=f"{safe_name}.epub",
                mime="application/epub+zip",
            )
        except requests.exceptions.RequestException as exc:
            st.error(f"Network error: {exc}")
        except ValueError as exc:
            st.error(f"Invalid URL: {exc}")
        except Exception as exc:
            st.error(f"Conversion failed: {exc}")
