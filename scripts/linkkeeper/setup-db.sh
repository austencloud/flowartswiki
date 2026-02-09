#!/usr/bin/env bash
set -euo pipefail

# LinkKeeper - One-time database setup
# Creates faw_link_archive and faw_link_queue tables, then runs initial sync
# from MediaWiki's externallinks table.
#
# Usage: bash scripts/linkkeeper/setup-db.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
SQL_FILE="$PROJECT_DIR/extensions/LinkHealth/sql/tables.sql"

cd "$PROJECT_DIR"
source .env

echo "[$(date)] LinkKeeper: Setting up database tables..."

# Replace MediaWiki placeholders with actual prefix (empty for this wiki)
PROCESSED_SQL=$(sed \
    -e 's|/\*_\*/||g' \
    -e 's|/\*\$wgDBTableOptions\*/|ENGINE=InnoDB, DEFAULT CHARSET=binary|g' \
    "$SQL_FILE")

echo "$PROCESSED_SQL" | docker compose exec -T db mariadb \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    "$DB_NAME"

echo "  Tables created."

# Verify
TABLES=$(docker compose exec -T db mariadb \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    "$DB_NAME" \
    -e "SHOW TABLES LIKE 'faw_%'")

echo "  Found tables:"
echo "$TABLES"

echo ""
echo "[$(date)] Running initial sync from externallinks..."
docker compose exec linkkeeper python linkkeeper.py sync-externallinks

echo "[$(date)] LinkKeeper database setup complete."
