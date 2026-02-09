#!/usr/bin/env python3
"""LinkKeeper CLI - External link preservation for Flow Arts Wiki.

Usage:
    linkkeeper.py process-queue [--batch N]
    linkkeeper.py check-links [--batch N]
    linkkeeper.py submit-archive [--batch N] [--dry-run]
    linkkeeper.py snapshot-critical [--domain DOMAIN] [--limit N]
    linkkeeper.py remediate-dead [--dry-run]
    linkkeeper.py sync-externallinks
    linkkeeper.py status
"""

import sys
import os
import argparse
import logging

# Add project root to path so lib/ and jobs/ are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_process_queue(args, config):
    from jobs.process_queue import run
    count = run(config, batch=args.batch)
    print(f"Processed {count} URLs from queue")


def cmd_check_links(args, config):
    from jobs.check_links import run
    count = run(config, batch=args.batch)
    print(f"Checked {count} URLs")


def cmd_submit_archive(args, config):
    from jobs.submit_archive import run
    count = run(config, batch=args.batch, dry_run=args.dry_run)
    print(f"Processed {count} URLs for archival")


def cmd_snapshot_critical(args, config):
    from jobs.snapshot_critical import run
    count = run(config, domain=args.domain, limit=args.limit)
    print(f"Captured {count} WARC snapshots")


def cmd_remediate_dead(args, config):
    from jobs.remediate_dead import run
    count = run(config, dry_run=args.dry_run)
    print(f"Remediated/flagged {count} dead links")


def cmd_sync_externallinks(args, config):
    from jobs.sync_externallinks import run
    count = run(config)
    print(f"Synced {count} URLs from externallinks")


def cmd_status(args, config):
    from lib.db import get_connection, execute_one
    conn = get_connection(config)

    total = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_archive")
    dead = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_archive WHERE la_is_dead = 1")
    archived = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_archive WHERE la_wayback_url IS NOT NULL")
    snapshotted = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_archive WHERE la_r2_key IS NOT NULL")
    remediated = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_archive WHERE la_remediated = 1")
    queued = execute_one(conn, "SELECT COUNT(*) as c FROM faw_link_queue")

    def val(row):
        return row.get("c", row.get(b"c", 0))

    print(f"LinkKeeper Status")
    print(f"  Total URLs:      {val(total)}")
    print(f"  Dead:            {val(dead)}")
    print(f"  Archived (IA):   {val(archived)}")
    print(f"  Snapshotted (R2):{val(snapshotted)}")
    print(f"  Remediated:      {val(remediated)}")
    print(f"  Queue pending:   {val(queued)}")

    # Top domains
    domains = execute_one(conn, """
        SELECT COUNT(DISTINCT la_domain) as c FROM faw_link_archive
    """)
    print(f"  Unique domains:  {val(domains)}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="LinkKeeper - Link preservation for Flow Arts Wiki")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    sub = parser.add_subparsers(dest="command")

    p_queue = sub.add_parser("process-queue", help="Process URL queue")
    p_queue.add_argument("--batch", type=int, default=200)

    p_check = sub.add_parser("check-links", help="Run health checks")
    p_check.add_argument("--batch", type=int, default=100)

    p_archive = sub.add_parser("submit-archive", help="Submit to Internet Archive")
    p_archive.add_argument("--batch", type=int, default=50)
    p_archive.add_argument("--dry-run", action="store_true")

    p_snapshot = sub.add_parser("snapshot-critical", help="WARC snapshot critical domains")
    p_snapshot.add_argument("--domain", type=str, default=None)
    p_snapshot.add_argument("--limit", type=int, default=None)

    p_remediate = sub.add_parser("remediate-dead", help="Remediate dead links")
    p_remediate.add_argument("--dry-run", action="store_true")

    sub.add_parser("sync-externallinks", help="Full sync from MW externallinks")
    sub.add_parser("status", help="Show LinkKeeper status")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    commands = {
        "process-queue": cmd_process_queue,
        "check-links": cmd_check_links,
        "submit-archive": cmd_submit_archive,
        "snapshot-critical": cmd_snapshot_critical,
        "remediate-dead": cmd_remediate_dead,
        "sync-externallinks": cmd_sync_externallinks,
        "status": cmd_status,
    }

    commands[args.command](args, config)


if __name__ == "__main__":
    main()
