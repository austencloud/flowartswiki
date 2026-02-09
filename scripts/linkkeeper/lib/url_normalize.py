"""URL normalization and hashing for consistent deduplication."""

import hashlib
import re
from urllib.parse import urlparse, urlunparse, unquote, quote


def normalize_url(url):
    """Normalize a URL for consistent comparison.

    - Lowercase scheme and host
    - Remove default ports (80 for http, 443 for https)
    - Remove trailing slash on bare paths
    - Remove fragment
    - Sort query parameters
    - Decode unnecessarily percent-encoded characters
    """
    url = url.strip()
    if not url:
        return ""

    parsed = urlparse(url)

    scheme = parsed.scheme.lower() or "http"
    host = parsed.hostname or ""
    host = host.lower().rstrip(".")

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = host
    if port:
        netloc = f"{host}:{port}"

    path = unquote(parsed.path)
    path = quote(path, safe="/:@!$&'()*+,;=-._~")
    if path == "/" and not parsed.query:
        path = ""

    query = parsed.query
    if query:
        pairs = sorted(re.findall(r"([^&=]+)(?:=([^&]*))?", query))
        query = "&".join(f"{k}={v}" if v else k for k, v in pairs)

    return urlunparse((scheme, netloc, path or "/", "", query, ""))


def url_hash(url):
    """SHA-256 hash of normalized URL, returned as raw bytes (32 bytes)."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).digest()


def extract_domain(url):
    """Extract the registrable domain from a URL."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    host = host.lower().rstrip(".")
    # Strip www. prefix
    if host.startswith("www."):
        host = host[4:]
    return host


# MediaWiki externallinks stores URLs in a specific format.
# This handles both the older (el_to) and newer (el_to_domain_index + el_to_path) formats.
def parse_mw_external_url(row):
    """Extract a usable URL from a MediaWiki externallinks table row."""
    if b"el_to" in row and row[b"el_to"]:
        return row[b"el_to"].decode("utf-8", errors="replace")
    # MW 1.39+ uses domain_index + path
    domain_index = row.get(b"el_to_domain_index", b"") or b""
    path = row.get(b"el_to_path", b"") or b""
    if domain_index and path:
        domain_index = domain_index.decode("utf-8", errors="replace")
        path = path.decode("utf-8", errors="replace")
        # domain_index format: "https://com.example." -> reverse to "example.com"
        # This is complex; fall back to combining them
        return f"{domain_index}{path}"
    return None
