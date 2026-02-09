"""Drain faw_link_queue into faw_link_archive.

Runs every 5 minutes. Picks up URLs queued by the PageSaveComplete hook
and upserts them into the canonical archive table.
"""

import logging

from lib.db import get_connection, execute, execute_one, execute_insert, now_ts
from lib.url_normalize import normalize_url, url_hash, extract_domain

logger = logging.getLogger("linkkeeper.process_queue")


def run(config, batch=200):
    """Process queued URLs into the archive table."""
    conn = get_connection(config)
    ts = now_ts()

    # Claim a batch
    execute(conn, """
        UPDATE faw_link_queue
        SET lq_claimed = %s
        WHERE lq_claimed IS NULL
        ORDER BY lq_id ASC
        LIMIT %s
    """, (ts, batch))

    rows = execute(conn, """
        SELECT lq_id, lq_url, lq_page_id
        FROM faw_link_queue
        WHERE lq_claimed = %s
    """, (ts,))

    if not rows:
        logger.debug("Queue empty, nothing to process")
        return 0

    processed = 0
    for row in rows:
        url = row[b"lq_url"].decode("utf-8", errors="replace") if isinstance(row[b"lq_url"], bytes) else row[b"lq_url"]
        page_id = row[b"lq_page_id"] if isinstance(row.get(b"lq_page_id"), int) else int(row.get("lq_page_id", row.get(b"lq_page_id", 0)))
        lq_id = row.get("lq_id", row.get(b"lq_id"))

        normalized = normalize_url(url)
        if not normalized:
            _delete_queue_item(conn, lq_id)
            continue

        h = url_hash(normalized)
        domain = extract_domain(normalized)

        existing = execute_one(conn, """
            SELECT la_id, la_page_ids FROM faw_link_archive
            WHERE la_url_hash = %s
        """, (h,))

        if existing:
            # Update page_ids set
            la_id = existing.get("la_id", existing.get(b"la_id"))
            page_ids_raw = existing.get("la_page_ids", existing.get(b"la_page_ids")) or b""
            page_ids = _parse_page_ids(page_ids_raw)
            page_ids.add(page_id)
            execute(conn, """
                UPDATE faw_link_archive
                SET la_page_ids = %s
                WHERE la_id = %s
            """, (_encode_page_ids(page_ids), la_id))
        else:
            execute_insert(conn, """
                INSERT INTO faw_link_archive
                    (la_url, la_url_hash, la_domain, la_first_seen, la_page_ids)
                VALUES (%s, %s, %s, %s, %s)
            """, (normalized.encode("utf-8"), h, domain.encode("utf-8"), ts, _encode_page_ids({page_id})))

        _delete_queue_item(conn, lq_id)
        processed += 1

    logger.info("Processed %d URLs from queue", processed)
    conn.close()
    return processed


def _delete_queue_item(conn, lq_id):
    execute(conn, "DELETE FROM faw_link_queue WHERE lq_id = %s", (lq_id,))


def _parse_page_ids(raw):
    """Parse comma-separated page IDs from blob."""
    if not raw:
        return set()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return {int(x) for x in raw.split(",") if x.strip().isdigit()}


def _encode_page_ids(ids):
    """Encode page ID set as comma-separated bytes."""
    return ",".join(str(x) for x in sorted(ids)).encode("utf-8")
