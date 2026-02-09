"""Full sync from MediaWiki's externallinks table.

Runs monthly (1st of month, 1 AM). Catches any URLs that were missed
by the PageSaveComplete hook (e.g., imported pages, API edits).
"""

import logging

from lib.db import get_connection, execute, execute_one, execute_insert, now_ts
from lib.url_normalize import normalize_url, url_hash, extract_domain

logger = logging.getLogger("linkkeeper.sync_externallinks")


def run(config):
    """Sync all external links from MediaWiki into faw_link_archive."""
    conn = get_connection(config)
    ts = now_ts()

    # MW 1.39+ uses el_to_domain_index + el_to_path, older uses el_to
    # Check which columns exist
    columns = execute(conn, """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'externallinks'
    """, (config["db_name"].encode("utf-8"),))

    col_names = {
        (c.get("COLUMN_NAME", c.get(b"COLUMN_NAME", b""))).decode("utf-8", errors="replace")
        if isinstance(c.get("COLUMN_NAME", c.get(b"COLUMN_NAME", b"")), bytes)
        else c.get("COLUMN_NAME", c.get(b"COLUMN_NAME", ""))
        for c in columns
    }

    has_el_to = "el_to" in col_names
    has_domain_index = "el_to_domain_index" in col_names

    if has_el_to:
        rows = execute(conn, """
            SELECT el_to, el_from FROM externallinks
            WHERE el_to IS NOT NULL
        """)
        url_key = "el_to"
    elif has_domain_index:
        rows = execute(conn, """
            SELECT el_to_domain_index, el_to_path, el_from FROM externallinks
            WHERE el_to_domain_index IS NOT NULL
        """)
        url_key = None  # handled specially
    else:
        logger.error("Cannot find URL columns in externallinks table")
        return 0

    inserted = 0
    updated = 0

    for row in rows:
        # Extract URL
        if url_key:
            raw_url = row.get(url_key, row.get(url_key.encode("utf-8"), b""))
        else:
            domain_idx = row.get("el_to_domain_index", row.get(b"el_to_domain_index", b""))
            path = row.get("el_to_path", row.get(b"el_to_path", b""))
            if isinstance(domain_idx, bytes):
                domain_idx = domain_idx.decode("utf-8", errors="replace")
            if isinstance(path, bytes):
                path = path.decode("utf-8", errors="replace")
            raw_url = f"{domain_idx}{path}"

        if isinstance(raw_url, bytes):
            raw_url = raw_url.decode("utf-8", errors="replace")

        page_id = row.get("el_from", row.get(b"el_from", 0))
        if isinstance(page_id, bytes):
            page_id = int(page_id)

        # Skip non-http URLs
        if not raw_url.startswith(("http://", "https://")):
            continue

        normalized = normalize_url(raw_url)
        if not normalized:
            continue

        h = url_hash(normalized)
        domain = extract_domain(normalized)

        existing = execute_one(conn, """
            SELECT la_id, la_page_ids FROM faw_link_archive
            WHERE la_url_hash = %s
        """, (h,))

        if existing:
            # Merge page_id
            la_id = existing.get("la_id", existing.get(b"la_id"))
            page_ids_raw = existing.get("la_page_ids", existing.get(b"la_page_ids")) or b""
            if isinstance(page_ids_raw, bytes):
                page_ids_raw = page_ids_raw.decode("utf-8", errors="replace")
            page_ids = {int(x) for x in page_ids_raw.split(",") if x.strip().isdigit()}
            if page_id not in page_ids:
                page_ids.add(page_id)
                execute(conn, """
                    UPDATE faw_link_archive SET la_page_ids = %s
                    WHERE la_id = %s
                """, (",".join(str(x) for x in sorted(page_ids)).encode("utf-8"), la_id))
                updated += 1
        else:
            execute_insert(conn, """
                INSERT INTO faw_link_archive
                    (la_url, la_url_hash, la_domain, la_first_seen, la_page_ids)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                normalized.encode("utf-8"),
                h,
                domain.encode("utf-8"),
                ts,
                str(page_id).encode("utf-8"),
            ))
            inserted += 1

    logger.info("Sync complete: %d inserted, %d updated", inserted, updated)
    conn.close()
    return inserted + updated
