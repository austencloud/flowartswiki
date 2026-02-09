"""Configuration from environment variables with graceful degradation."""

import os
import logging

logger = logging.getLogger("linkkeeper.config")


def load_config():
    """Load configuration from environment variables.

    Returns a dict with all config values. Missing optional values
    are None, enabling graceful degradation (Tier 0-3).
    """
    config = {
        # Required: Database (always available via Docker network)
        "db_host": os.environ.get("DB_HOST", "db"),
        "db_port": int(os.environ.get("DB_PORT", "3306")),
        "db_user": os.environ.get("DB_USER", "wiki"),
        "db_password": os.environ.get("DB_PASSWORD", ""),
        "db_name": os.environ.get("DB_NAME", "flowartswiki"),

        # Tier 1: Internet Archive (optional)
        "ia_access_key": os.environ.get("IA_ACCESS_KEY"),
        "ia_secret_key": os.environ.get("IA_SECRET_KEY"),

        # Tier 2: Cloudflare R2 for WARC snapshots (optional)
        "r2_endpoint": os.environ.get("R2_ENDPOINT"),
        "r2_access_key": os.environ.get("R2_ACCESS_KEY"),
        "r2_secret_key": os.environ.get("R2_SECRET_KEY"),
        "r2_bucket": os.environ.get("R2_BUCKET", "flowartswiki-backups"),

        # Tier 3: MediaWiki bot account (optional)
        "wiki_bot_user": os.environ.get("WIKI_BOT_USER"),
        "wiki_bot_password": os.environ.get("WIKI_BOT_PASSWORD"),
        "wiki_api": os.environ.get("WIKI_API", "http://mediawiki/api.php"),
    }

    # Log active tier
    tier = 0
    if config["ia_access_key"] and config["ia_secret_key"]:
        tier = 1
    if tier >= 1 and config["r2_access_key"] and config["r2_secret_key"]:
        tier = 2
    if tier >= 1 and config["wiki_bot_user"] and config["wiki_bot_password"]:
        tier = 3

    logger.info("LinkKeeper operating at Tier %d", tier)
    if tier < 1:
        logger.info("  Tier 1 (IA archival) disabled: set IA_ACCESS_KEY + IA_SECRET_KEY")
    if tier < 2:
        logger.info("  Tier 2 (WARC snapshots) disabled: set R2_ACCESS_KEY + R2_SECRET_KEY")
    if tier < 3:
        logger.info("  Tier 3 (auto-remediation) disabled: set WIKI_BOT_USER + WIKI_BOT_PASSWORD")

    return config
