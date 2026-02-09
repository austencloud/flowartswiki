"""HTTP health checking with redirect following and soft-404 detection."""

import re
import time
import logging
from collections import defaultdict

import requests

logger = logging.getLogger("linkkeeper.http_check")

# Per-domain rate limiting: max 2 req/sec
_domain_last_request = defaultdict(float)
_DOMAIN_MIN_INTERVAL = 0.5  # seconds between requests to same domain

SOFT_404_PATTERNS = re.compile(
    r"page\s*not\s*found|"
    r"404\s*(error|not\s*found)|"
    r"doesn.t\s*exist|"
    r"no\s*longer\s*available|"
    r"has\s*been\s*(removed|deleted)|"
    r"this\s*page\s*(is\s*)?no\s*longer",
    re.IGNORECASE,
)

USER_AGENT = (
    "LinkKeeper/1.0 (https://flowarts.wiki; link preservation bot) "
    "Mozilla/5.0 (compatible)"
)

# Domains known to block HEAD requests
HEAD_BLACKLIST = {"tumblr.com", "wordpress.com", "blogspot.com"}


def _rate_limit(domain):
    """Sleep if needed to respect per-domain rate limit."""
    now = time.monotonic()
    elapsed = now - _domain_last_request[domain]
    if elapsed < _DOMAIN_MIN_INTERVAL:
        time.sleep(_DOMAIN_MIN_INTERVAL - elapsed)
    _domain_last_request[domain] = time.monotonic()


def _should_skip_head(domain):
    """Check if domain is known to block HEAD requests."""
    return any(domain.endswith(d) for d in HEAD_BLACKLIST)


def check_url(url, domain=None, timeout=15):
    """Check if a URL is alive.

    Returns dict with:
        status: HTTP status code (0 for connection error)
        alive: bool
        soft_404: bool
        redirect_url: final URL if redirected, else None
        error: error message if connection failed
    """
    if domain is None:
        from .url_normalize import extract_domain
        domain = extract_domain(url)

    _rate_limit(domain)

    headers = {"User-Agent": USER_AGENT}
    result = {
        "status": 0,
        "alive": False,
        "soft_404": False,
        "redirect_url": None,
        "error": None,
    }

    try:
        # Try HEAD first (cheaper), fall back to GET
        if not _should_skip_head(domain):
            try:
                resp = requests.head(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                if resp.status_code < 400:
                    result["status"] = resp.status_code
                    result["alive"] = True
                    if resp.url != url:
                        result["redirect_url"] = resp.url
                    return result
                # If HEAD returns error, try GET (some servers reject HEAD)
                if resp.status_code == 405:
                    pass  # fall through to GET
                else:
                    result["status"] = resp.status_code
                    return result
            except requests.RequestException:
                pass  # fall through to GET

        # GET request
        resp = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        result["status"] = resp.status_code

        if resp.url != url:
            result["redirect_url"] = resp.url

        if resp.status_code >= 400:
            return result

        # Soft 404 detection: check small pages for "not found" language
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) < 1024:
            body = resp.text[:1024]
            if SOFT_404_PATTERNS.search(body):
                result["soft_404"] = True
                result["alive"] = False
                return result

        # If no Content-Length header, read a chunk
        if content_length is None:
            body = resp.text[:2048]
            if len(body) < 1024 and SOFT_404_PATTERNS.search(body):
                result["soft_404"] = True
                result["alive"] = False
                return result

        result["alive"] = True

    except requests.ConnectionError as e:
        result["error"] = f"Connection error: {e}"
    except requests.Timeout:
        result["error"] = "Timeout"
    except requests.RequestException as e:
        result["error"] = str(e)

    return result
