"""WARC snapshots of priority domains to R2.

Runs weekly (Sunday 2:30 AM). Captures pages from high-risk domains
as local WARC archives, independent of archive.org.
"""

import os
import logging

from lib.db import get_connection, execute, now_ts
from lib.warc_writer import capture_url_to_warc
from lib.r2_client import get_r2_client, upload_warc

logger = logging.getLogger("linkkeeper.snapshot_critical")

PRIORITY_DOMAINS = [
    "drexfactor.com",
    "sirlorq.wordpress.com",
    "spinscience.xyz",
    "noelyee.com",
    "playpoi.com",
    "flowartsinstitute.com",
    "homeofpoi.com",
    "poividoftheday.tumblr.com",
    "wickup.wordpress.com",
    "tabjuggler.tumblr.com",
    "flamebuoyant.com",
]


def run(config, domain=None, limit=None):
    """Capture WARC snapshots of critical domain URLs and upload to R2."""
    r2_endpoint = config.get("r2_endpoint")
    r2_access = config.get("r2_access_key")
    r2_secret = config.get("r2_secret_key")
    r2_bucket = config.get("r2_bucket")

    if not all([r2_endpoint, r2_access, r2_secret, r2_bucket]):
        logger.warning("R2 not configured, skipping WARC snapshots")
        return 0

    conn = get_connection(config)
    ts = now_ts()

    # Build domain filter
    if domain:
        domains = [domain]
    else:
        domains = PRIORITY_DOMAINS

    domain_placeholders = ",".join(["%s"] * len(domains))

    rows = execute(conn, f"""
        SELECT la_id, la_url, la_domain
        FROM faw_link_archive
        WHERE la_is_dead = 0
          AND la_domain IN ({domain_placeholders})
        ORDER BY la_r2_ts ASC, la_id ASC
    """, tuple(d.encode("utf-8") if isinstance(d, str) else d for d in domains))

    if limit:
        rows = rows[:limit]

    if not rows:
        logger.debug("No critical URLs to snapshot")
        return 0

    r2 = get_r2_client({
        "r2_endpoint": r2_endpoint,
        "r2_access_key": r2_access,
        "r2_secret_key": r2_secret,
    })

    captured = 0
    warc_dir = "/tmp/linkkeeper-warcs"

    for row in rows:
        la_id = row.get("la_id", row.get(b"la_id"))
        url = row.get("la_url", row.get(b"la_url"))
        if isinstance(url, bytes):
            url = url.decode("utf-8", errors="replace")
        url_domain = row.get("la_domain", row.get(b"la_domain"))
        if isinstance(url_domain, bytes):
            url_domain = url_domain.decode("utf-8", errors="replace")

        warc_result = capture_url_to_warc(url, output_dir=warc_dir)
        if not warc_result["success"]:
            logger.warning("WARC capture failed for %s: %s", url, warc_result["error"])
            continue

        # Upload to R2
        r2_key = f"warcs/{url_domain}/{os.path.basename(warc_result['path'])}"
        upload_result = upload_warc(r2, r2_bucket, r2_key, warc_result["path"])

        if upload_result["success"]:
            execute(conn, """
                UPDATE faw_link_archive SET
                    la_r2_key = %s,
                    la_r2_ts = %s,
                    la_r2_size = %s
                WHERE la_id = %s
            """, (r2_key.encode("utf-8"), ts, upload_result["size"], la_id))
            captured += 1
        else:
            logger.warning("R2 upload failed for %s: %s", url, upload_result["error"])

        # Clean up local WARC file
        try:
            os.remove(warc_result["path"])
        except OSError:
            pass

    logger.info("Captured and uploaded %d WARC snapshots", captured)
    conn.close()
    return captured
