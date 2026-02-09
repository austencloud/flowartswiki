"""Submit URLs to Internet Archive via CDX lookup + SPN2.

Runs every 6 hours. Checks CDX first (free), only submits to SPN2 if
no recent snapshot exists. 50 URLs per batch.
"""

import logging

from lib.db import get_connection, execute, now_ts
from lib.wayback import cdx_lookup, submit_spn2

logger = logging.getLogger("linkkeeper.submit_archive")

# Only submit to SPN2 if last snapshot is older than 90 days
STALE_DAYS = 90


def run(config, batch=50, dry_run=False):
    """Check and submit URLs to Internet Archive."""
    conn = get_connection(config)
    ts = now_ts()

    ia_access = config.get("ia_access_key")
    ia_secret = config.get("ia_secret_key")
    has_ia_keys = bool(ia_access and ia_secret)

    # Get URLs that haven't been checked with CDX recently
    # or have never been submitted
    rows = execute(conn, """
        SELECT la_id, la_url, la_spn2_status, la_wayback_ts
        FROM faw_link_archive
        WHERE la_is_dead = 0
          AND (la_spn2_status = 'none' OR la_spn2_status = 'error')
        ORDER BY la_spn2_last ASC, la_id ASC
        LIMIT %s
    """, (batch,))

    if not rows:
        logger.debug("No URLs need archival")
        return 0

    processed = 0
    submitted = 0

    for row in rows:
        la_id = row.get("la_id", row.get(b"la_id"))
        url = row.get("la_url", row.get(b"la_url"))
        if isinstance(url, bytes):
            url = url.decode("utf-8", errors="replace")

        # Step 1: CDX lookup (always free)
        snapshot = cdx_lookup(url)

        if snapshot:
            wayback_url = snapshot["wayback_url"]
            wayback_ts = snapshot["timestamp"]

            execute(conn, """
                UPDATE faw_link_archive SET
                    la_wayback_url = %s,
                    la_wayback_ts = %s,
                    la_spn2_status = 'success',
                    la_spn2_last = %s
                WHERE la_id = %s
            """, (
                wayback_url.encode("utf-8"),
                wayback_ts.encode("utf-8") if isinstance(wayback_ts, str) else wayback_ts,
                ts,
                la_id,
            ))

            # Check if snapshot is recent enough
            if _is_recent(wayback_ts, STALE_DAYS):
                logger.debug("Recent snapshot exists for %s", url)
                processed += 1
                continue

        # Step 2: SPN2 submission (requires IA keys)
        if not has_ia_keys:
            logger.debug("No IA keys, skipping SPN2 for %s", url)
            processed += 1
            continue

        if dry_run:
            logger.info("[DRY RUN] Would submit to SPN2: %s", url)
            processed += 1
            continue

        result = submit_spn2(url, ia_access, ia_secret)

        if result["success"]:
            execute(conn, """
                UPDATE faw_link_archive SET
                    la_spn2_status = 'pending',
                    la_spn2_last = %s
                WHERE la_id = %s
            """, (ts, la_id))
            submitted += 1
        else:
            execute(conn, """
                UPDATE faw_link_archive SET
                    la_spn2_status = 'error',
                    la_spn2_last = %s
                WHERE la_id = %s
            """, (ts, la_id))

        processed += 1

    logger.info("Processed %d URLs, submitted %d to SPN2", processed, submitted)
    conn.close()
    return processed


def _is_recent(wayback_ts, max_days):
    """Check if a Wayback timestamp is within max_days of now."""
    from datetime import datetime, timezone, timedelta

    if not wayback_ts:
        return False
    if isinstance(wayback_ts, bytes):
        wayback_ts = wayback_ts.decode("utf-8")
    try:
        snapshot_dt = datetime.strptime(wayback_ts[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        return snapshot_dt > cutoff
    except (ValueError, IndexError):
        return False
