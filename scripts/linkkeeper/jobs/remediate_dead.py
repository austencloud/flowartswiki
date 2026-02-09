"""Remediate confirmed-dead links in wiki pages.

Runs weekly (Monday 5 AM). Two modes:
- Auto-fix: For {{cite web}} templates, adds archive-url/archive-date/url-status=dead
- Flag for review: For bare links, writes to Project:LinkKeeper/Review
"""

import re
import logging

import requests

from lib.db import get_connection, execute, now_ts

logger = logging.getLogger("linkkeeper.remediate_dead")

# Only remediate URLs that have been dead for 30+ days with 7+ failures
MIN_DEAD_DAYS = 30
MIN_FAILURES = 7

# Regex to find {{cite web}} templates containing a specific URL
CITE_WEB_PATTERN = re.compile(
    r"(\{\{cite web\s*\|[^}]*?\|?\s*url\s*=\s*)(https?://[^\s|}\]]+)([^}]*\}\})",
    re.IGNORECASE | re.DOTALL,
)


def run(config, dry_run=False):
    """Remediate dead links with archive URLs."""
    conn = get_connection(config)
    ts = now_ts()

    bot_user = config.get("wiki_bot_user")
    bot_password = config.get("wiki_bot_password")
    wiki_api = config.get("wiki_api", "http://mediawiki/api.php")

    if not all([bot_user, bot_password]) and not dry_run:
        logger.warning("Bot credentials not configured, running in dry-run mode")
        dry_run = True

    # Find dead URLs with wayback snapshots that haven't been remediated
    rows = execute(conn, """
        SELECT la_id, la_url, la_wayback_url, la_wayback_ts,
               la_dead_since, la_consecutive_failures, la_page_ids
        FROM faw_link_archive
        WHERE la_is_dead = 1
          AND la_remediated = 0
          AND la_wayback_url IS NOT NULL
          AND la_consecutive_failures >= %s
    """, (MIN_FAILURES,))

    # Filter by dead duration
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_DEAD_DAYS)
    cutoff_ts = cutoff.strftime("%Y%m%d%H%M%S")

    eligible = []
    for row in rows:
        dead_since = row.get("la_dead_since", row.get(b"la_dead_since"))
        if isinstance(dead_since, bytes):
            dead_since = dead_since.decode("utf-8")
        if dead_since and dead_since <= cutoff_ts:
            eligible.append(row)

    if not eligible:
        logger.debug("No dead links eligible for remediation")
        return 0

    # Get bot session if not dry run
    session = None
    if not dry_run:
        session = _get_bot_session(wiki_api, bot_user, bot_password)
        if not session:
            logger.error("Failed to authenticate bot")
            return 0

    remediated = 0
    flagged = 0
    review_entries = []

    for row in eligible:
        la_id = row.get("la_id", row.get(b"la_id"))
        url = row.get("la_url", row.get(b"la_url"))
        if isinstance(url, bytes):
            url = url.decode("utf-8", errors="replace")
        wayback_url = row.get("la_wayback_url", row.get(b"la_wayback_url"))
        if isinstance(wayback_url, bytes):
            wayback_url = wayback_url.decode("utf-8", errors="replace")
        wayback_ts = row.get("la_wayback_ts", row.get(b"la_wayback_ts"))
        if isinstance(wayback_ts, bytes):
            wayback_ts = wayback_ts.decode("utf-8", errors="replace")
        page_ids_raw = row.get("la_page_ids", row.get(b"la_page_ids")) or b""
        if isinstance(page_ids_raw, bytes):
            page_ids_raw = page_ids_raw.decode("utf-8", errors="replace")

        page_ids = [int(x) for x in page_ids_raw.split(",") if x.strip().isdigit()]

        archive_date = _format_archive_date(wayback_ts)

        for page_id in page_ids:
            if dry_run:
                content = _get_page_content_dry(conn, page_id)
            else:
                content = _get_page_content(session, wiki_api, page_id)

            if not content:
                continue

            # Try auto-fix for cite web templates
            new_content, fixed = _fix_cite_web(content, url, wayback_url, archive_date)
            if fixed:
                if dry_run:
                    logger.info("[DRY RUN] Would auto-fix cite web on page %d for %s", page_id, url)
                else:
                    _save_page(session, wiki_api, page_id, new_content,
                               f"LinkKeeper: Added archive URL for dead link {url}")
                remediated += 1
            else:
                # Flag for human review
                review_entries.append({
                    "url": url,
                    "wayback_url": wayback_url,
                    "page_id": page_id,
                })
                flagged += 1

        # Mark as remediated
        execute(conn, """
            UPDATE faw_link_archive SET
                la_remediated = 1,
                la_remediated_ts = %s
            WHERE la_id = %s
        """, (ts, la_id))

    # Write review page if there are flagged links
    if review_entries and not dry_run:
        _write_review_page(session, wiki_api, review_entries)

    logger.info("Remediated %d links, flagged %d for review", remediated, flagged)
    conn.close()
    return remediated + flagged


def _fix_cite_web(content, dead_url, wayback_url, archive_date):
    """Add archive-url to a cite web template containing the dead URL."""
    if dead_url not in content:
        return content, False

    # Check if already has archive-url
    if "archive-url" in content and wayback_url in content:
        return content, False

    def replace_cite(match):
        prefix = match.group(1)
        url = match.group(2)
        suffix = match.group(3)

        if url.rstrip("/") != dead_url.rstrip("/"):
            return match.group(0)

        # Don't double-add
        if "archive-url" in suffix:
            return match.group(0)

        archive_params = (
            f" |archive-url={wayback_url}"
            f" |archive-date={archive_date}"
            f" |url-status=dead"
        )
        return f"{prefix}{url}{archive_params}{suffix}"

    new_content = CITE_WEB_PATTERN.sub(replace_cite, content)
    return new_content, new_content != content


def _format_archive_date(wayback_ts):
    """Format a Wayback timestamp as a human-readable date."""
    if not wayback_ts or len(wayback_ts) < 8:
        return "unknown"
    return f"{wayback_ts[:4]}-{wayback_ts[4:6]}-{wayback_ts[6:8]}"


def _get_bot_session(api_url, username, password):
    """Authenticate with the MediaWiki API and return a session."""
    session = requests.Session()
    try:
        # Get login token
        resp = session.get(api_url, params={
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        })
        login_token = resp.json()["query"]["tokens"]["logintoken"]

        # Login
        resp = session.post(api_url, data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        })
        result = resp.json().get("login", {}).get("result")
        if result == "Success":
            return session
        logger.error("Bot login failed: %s", result)
        return None
    except Exception as e:
        logger.error("Bot authentication error: %s", e)
        return None


def _get_page_content(session, api_url, page_id):
    """Get wikitext content of a page by ID."""
    try:
        resp = session.get(api_url, params={
            "action": "query",
            "pageids": page_id,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
        })
        pages = resp.json().get("query", {}).get("pages", {})
        page = pages.get(str(page_id), {})
        revisions = page.get("revisions", [])
        if revisions:
            return revisions[0].get("slots", {}).get("main", {}).get("*", "")
        return None
    except Exception as e:
        logger.error("Failed to get page %d content: %s", page_id, e)
        return None


def _get_page_content_dry(conn, page_id):
    """Placeholder for dry-run mode - returns empty string."""
    return ""


def _save_page(session, api_url, page_id, content, summary):
    """Save wikitext content to a page."""
    try:
        # Get CSRF token
        resp = session.get(api_url, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        })
        csrf_token = resp.json()["query"]["tokens"]["csrftoken"]

        resp = session.post(api_url, data={
            "action": "edit",
            "pageid": page_id,
            "text": content,
            "summary": summary,
            "bot": 1,
            "token": csrf_token,
            "format": "json",
        })
        result = resp.json().get("edit", {}).get("result")
        if result != "Success":
            logger.error("Failed to save page %d: %s", page_id, resp.json())
    except Exception as e:
        logger.error("Error saving page %d: %s", page_id, e)


def _write_review_page(session, api_url, entries):
    """Write or append to the Project:LinkKeeper/Review maintenance page."""
    from datetime import datetime, timezone

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"\n== Review batch {date} ==\n"]
    for entry in entries:
        lines.append(
            f"* [[Special:Redirect/page/{entry['page_id']}|Page {entry['page_id']}]]: "
            f"<code>{entry['url']}</code> → [https:{entry['wayback_url']} archive]\n"
        )

    new_section = "".join(lines)

    # Get existing content
    existing = _get_page_content_by_title(session, api_url, "Project:LinkKeeper/Review")
    if existing:
        content = existing + "\n" + new_section
    else:
        content = (
            "{{Notice|This page is maintained by the LinkKeeper bot. "
            "Review dead links below and approve fixes.}}\n\n"
            + new_section
        )

    _save_page_by_title(session, api_url, "Project:LinkKeeper/Review", content,
                         "LinkKeeper: Added dead links for review")


def _get_page_content_by_title(session, api_url, title):
    """Get wikitext by page title."""
    try:
        resp = session.get(api_url, params={
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
        })
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            revisions = page.get("revisions", [])
            if revisions:
                return revisions[0].get("slots", {}).get("main", {}).get("*", "")
        return None
    except Exception:
        return None


def _save_page_by_title(session, api_url, title, content, summary):
    """Save wikitext to a page by title."""
    try:
        resp = session.get(api_url, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        })
        csrf_token = resp.json()["query"]["tokens"]["csrftoken"]

        session.post(api_url, data={
            "action": "edit",
            "title": title,
            "text": content,
            "summary": summary,
            "bot": 1,
            "token": csrf_token,
            "format": "json",
        })
    except Exception as e:
        logger.error("Error saving page %s: %s", title, e)
