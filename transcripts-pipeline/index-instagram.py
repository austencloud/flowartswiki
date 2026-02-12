#!/usr/bin/env python3
"""
Index public Instagram accounts for the Flow Arts Wiki.

For each account in instagram-accounts.json, fetches post metadata (URL, caption,
date, type) and saves to instagram-index.tsv. Optionally archives posts to the
Wayback Machine.

Usage:
    python index-instagram.py                    # Index all accounts
    python index-instagram.py trideas            # Index one account
    python index-instagram.py --archive trideas  # Index + Wayback archive
    python index-instagram.py --login            # Login first (required by Instagram)

First-time setup:
    python index-instagram.py --login
    (Enter your Instagram username and password when prompted.
     Session is saved locally so you only need to do this once.)
"""

import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

try:
    import instaloader
except ImportError:
    print("Error: instaloader not installed. Run: pip install instaloader")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
ACCOUNTS_FILE = SCRIPT_DIR / "instagram-accounts.json"
INDEX_FILE = SCRIPT_DIR / "instagram-index.tsv"
CAPTIONS_DIR = SCRIPT_DIR / "instagram-captions"
SESSION_DIR = SCRIPT_DIR / ".instagram-session"

def load_accounts(filter_handle=None):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    if filter_handle:
        accounts = [a for a in accounts if a["handle"] == filter_handle]
        if not accounts:
            print(f"Account '{filter_handle}' not found in instagram-accounts.json")
            sys.exit(1)
    return accounts

def load_existing_index():
    """Load already-indexed post shortcodes to avoid re-fetching."""
    existing = set()
    if INDEX_FILE.exists():
        with open(INDEX_FILE, encoding="utf-8") as f:
            for line in f:
                if line.startswith("handle\t"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    existing.add(parts[1])  # shortcode column
    return existing

def index_account(L, handle, existing_shortcodes):
    """Fetch public post metadata for an account."""
    print(f"\nIndexing @{handle}...")
    try:
        profile = instaloader.Profile.from_username(L.context, handle)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"  Profile @{handle} does not exist or is private")
        return []

    if profile.is_private:
        print(f"  @{handle} is private, skipping")
        return []

    print(f"  {profile.mediacount} posts, {profile.followers} followers")

    posts = []
    count = 0
    skipped = 0

    for post in profile.get_posts():
        if post.shortcode in existing_shortcodes:
            skipped += 1
            continue

        caption = (post.caption or "").replace("\t", " ").replace("\n", " | ")
        # Truncate very long captions for the TSV (full caption saved separately)
        caption_short = caption[:300] + "..." if len(caption) > 300 else caption

        post_type = "reel" if post.is_video else "image"
        if post.typename == "GraphSidecar":
            post_type = "carousel"

        row = {
            "handle": handle,
            "shortcode": post.shortcode,
            "date": post.date_utc.strftime("%Y-%m-%d"),
            "type": post_type,
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "caption": caption_short,
            "likes": post.likes,
            "comments": post.comments,
        }
        posts.append(row)

        # Save full caption to file
        caption_dir = CAPTIONS_DIR / handle
        caption_dir.mkdir(parents=True, exist_ok=True)
        caption_file = caption_dir / f"{post.shortcode}.txt"
        if not caption_file.exists():
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(f"Date: {row['date']}\n")
                f.write(f"URL: {row['url']}\n")
                f.write(f"Type: {post_type}\n")
                f.write(f"---\n")
                f.write(post.caption or "(no caption)")

        count += 1
        if count % 10 == 0:
            print(f"  {count} posts indexed...")

        # Rate limiting - Instagram throttles aggressive scraping
        time.sleep(1.5)

    print(f"  Done: {count} new, {skipped} already indexed")
    return posts

def archive_to_wayback(url):
    """Submit a URL to the Wayback Machine's Save Page Now."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"https://web.archive.org/save/{url}",
            method="GET"
        )
        req.add_header("User-Agent", "FlowArtsWiki/1.0 (archival)")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  Wayback save failed for {url}: {e}")
        return False

def main():
    do_archive = "--archive" in sys.argv
    do_login = "--login" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    filter_handle = args[0] if args else None

    accounts = load_accounts(filter_handle) if not do_login else []
    existing = load_existing_index()

    # Initialize instaloader
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    # Load or create session
    SESSION_DIR.mkdir(exist_ok=True)
    session_file = SESSION_DIR / "session"
    if do_login:
        username = input("Instagram username: ")
        L.login(username, input("Instagram password: "))
        L.save_session_to_file(str(session_file))
        print(f"Session saved. You can now run without --login.")
        if not filter_handle:
            return
    elif session_file.exists():
        try:
            L.load_session_from_file(str(session_file))
            print("Loaded saved Instagram session.")
        except Exception as e:
            print(f"Warning: Could not load session ({e}). Running without login.")
            print("If you get 401 errors, run: python index-instagram.py --login")
    else:
        print("No Instagram session found. If you get 401 errors, run:")
        print("  python index-instagram.py --login")

    all_posts = []
    for account in accounts:
        posts = index_account(L, account["handle"], existing)
        all_posts.extend(posts)

    if not all_posts:
        print("\nNo new posts to index.")
        return

    # Append to TSV
    write_header = not INDEX_FILE.exists()
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        if write_header:
            f.write("handle\tshortcode\tdate\ttype\turl\tcaption\tlikes\tcomments\n")
        for p in all_posts:
            f.write(f"{p['handle']}\t{p['shortcode']}\t{p['date']}\t{p['type']}\t{p['url']}\t{p['caption']}\t{p['likes']}\t{p['comments']}\n")

    print(f"\n=== Indexed {len(all_posts)} new posts ===")
    print(f"Total in index: {len(existing) + len(all_posts)}")
    print(f"Captions saved to: {CAPTIONS_DIR}/")

    # Optional Wayback archival
    if do_archive:
        print(f"\nArchiving {len(all_posts)} posts to Wayback Machine...")
        archived = 0
        for p in all_posts:
            if archive_to_wayback(p["url"]):
                archived += 1
                print(f"  Archived: {p['url']}")
            time.sleep(5)  # Wayback rate limit
        print(f"Archived {archived}/{len(all_posts)} posts")

if __name__ == "__main__":
    main()
