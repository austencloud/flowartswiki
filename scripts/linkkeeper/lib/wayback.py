"""Internet Archive Wayback Machine CDX API + SPN2 client."""

import time
import logging

import requests

logger = logging.getLogger("linkkeeper.wayback")

CDX_API = "https://web.archive.org/cdx/search/cdx"
SPN2_API = "https://web.archive.org/save"
AVAILABILITY_API = "https://archive.org/wayback/available"

# SPN2 rate limit: 12/min (below the 15/min cap)
_SPN2_MIN_INTERVAL = 5.0  # seconds between SPN2 submissions
_last_spn2 = 0.0


def cdx_lookup(url, limit=1):
    """Look up a URL in the Wayback Machine CDX index.

    Returns the most recent snapshot info or None.
    """
    try:
        resp = requests.get(
            CDX_API,
            params={
                "url": url,
                "output": "json",
                "limit": limit,
                "fl": "timestamp,original,statuscode,mimetype",
                "sort": "reverse",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("CDX lookup failed for %s: HTTP %d", url, resp.status_code)
            return None

        rows = resp.json()
        if len(rows) < 2:  # first row is header
            return None

        header, row = rows[0], rows[1]
        result = dict(zip(header, row))
        ts = result.get("timestamp", "")
        original = result.get("original", url)
        return {
            "timestamp": ts,
            "wayback_url": f"https://web.archive.org/web/{ts}/{original}",
            "status": result.get("statuscode", ""),
        }
    except requests.RequestException as e:
        logger.warning("CDX lookup error for %s: %s", url, e)
        return None


def check_availability(url):
    """Quick availability check via Wayback Availability API."""
    try:
        resp = requests.get(
            AVAILABILITY_API,
            params={"url": url},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        snapshot = data.get("archived_snapshots", {}).get("closest")
        if snapshot and snapshot.get("available"):
            return {
                "timestamp": snapshot.get("timestamp", ""),
                "wayback_url": snapshot.get("url", ""),
                "status": snapshot.get("status", ""),
            }
        return None
    except requests.RequestException as e:
        logger.warning("Availability check error for %s: %s", url, e)
        return None


def submit_spn2(url, access_key, secret_key):
    """Submit a URL to Save Page Now 2 (SPN2).

    Returns dict with:
        success: bool
        job_id: SPN2 job ID if submitted
        error: error message if failed
    """
    global _last_spn2
    elapsed = time.monotonic() - _last_spn2
    if elapsed < _SPN2_MIN_INTERVAL:
        time.sleep(_SPN2_MIN_INTERVAL - elapsed)

    result = {"success": False, "job_id": None, "error": None}

    try:
        resp = requests.post(
            SPN2_API,
            data={"url": url, "capture_all": 1},
            headers={
                "Authorization": f"LOW {access_key}:{secret_key}",
                "Accept": "application/json",
            },
            timeout=30,
        )
        _last_spn2 = time.monotonic()

        if resp.status_code == 200:
            data = resp.json()
            result["success"] = True
            result["job_id"] = data.get("job_id")
        elif resp.status_code == 429:
            result["error"] = "Rate limited by SPN2"
            logger.warning("SPN2 rate limited for %s", url)
        else:
            result["error"] = f"SPN2 HTTP {resp.status_code}: {resp.text[:200]}"
            logger.warning("SPN2 error for %s: %s", url, result["error"])

    except requests.RequestException as e:
        _last_spn2 = time.monotonic()
        result["error"] = str(e)
        logger.warning("SPN2 request error for %s: %s", url, e)

    return result
