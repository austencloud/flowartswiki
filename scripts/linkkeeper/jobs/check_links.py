"""HTTP health checks for archived URLs.

Runs every 4 hours. Checks 100 URLs per batch, oldest-checked first.
After 3 consecutive failures, marks the URL as dead.
"""

import logging

from lib.db import get_connection, execute, now_ts
from lib.http_check import check_url
from lib.url_normalize import extract_domain

logger = logging.getLogger("linkkeeper.check_links")

DEAD_THRESHOLD = 3  # consecutive failures before marking dead


def run(config, batch=100):
    """Run health checks on the oldest-checked URLs."""
    conn = get_connection(config)
    ts = now_ts()

    rows = execute(conn, """
        SELECT la_id, la_url, la_domain, la_consecutive_failures
        FROM faw_link_archive
        ORDER BY la_last_checked ASC, la_id ASC
        LIMIT %s
    """, (batch,))

    if not rows:
        logger.debug("No URLs to check")
        return 0

    checked = 0
    newly_dead = 0

    for row in rows:
        la_id = row.get("la_id", row.get(b"la_id"))
        url = row.get("la_url", row.get(b"la_url"))
        if isinstance(url, bytes):
            url = url.decode("utf-8", errors="replace")
        domain = row.get("la_domain", row.get(b"la_domain"))
        if isinstance(domain, bytes):
            domain = domain.decode("utf-8", errors="replace")
        prev_failures = row.get("la_consecutive_failures", row.get(b"la_consecutive_failures", 0))

        result = check_url(url, domain=domain)

        if result["alive"] and not result["soft_404"]:
            # URL is healthy - reset failure counter
            execute(conn, """
                UPDATE faw_link_archive SET
                    la_http_status = %s,
                    la_last_checked = %s,
                    la_consecutive_failures = 0,
                    la_is_dead = 0,
                    la_dead_since = NULL,
                    la_soft_404 = 0
                WHERE la_id = %s
            """, (result["status"], ts, la_id))
        else:
            # URL failed
            new_failures = prev_failures + 1
            is_dead = 1 if new_failures >= DEAD_THRESHOLD else 0
            soft_404 = 1 if result["soft_404"] else 0

            update_fields = {
                "la_http_status": result["status"],
                "la_last_checked": ts,
                "la_consecutive_failures": new_failures,
                "la_is_dead": is_dead,
                "la_soft_404": soft_404,
            }

            # Only set dead_since on the transition to dead
            if is_dead and new_failures == DEAD_THRESHOLD:
                update_fields["la_dead_since"] = ts
                newly_dead += 1
                logger.warning("URL confirmed dead: %s (status=%s)", url, result["status"])

            set_clause = ", ".join(f"{k} = %s" for k in update_fields)
            execute(conn, f"""
                UPDATE faw_link_archive SET {set_clause}
                WHERE la_id = %s
            """, (*update_fields.values(), la_id))

        checked += 1

    logger.info("Checked %d URLs, %d newly dead", checked, newly_dead)
    conn.close()
    return checked
