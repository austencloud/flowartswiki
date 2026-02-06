#!/usr/bin/env bash
set -euo pipefail

# Flow Arts Wiki - Restore from Backup
# Usage:
#   bash scripts/restore.sh                    # Restore latest local backup
#   bash scripts/restore.sh 2026-02-05_0300    # Restore specific date
#   bash scripts/restore.sh --from-r2          # Download latest from R2, then restore
#   bash scripts/restore.sh --from-r2 2026-02-05_0300  # Download specific date from R2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

cd "$PROJECT_DIR"
source .env

FROM_R2=false
TARGET_DATE=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --from-r2) FROM_R2=true; shift ;;
        *) TARGET_DATE="$1"; shift ;;
    esac
done

# ---------------------------------------------------------------
# 1. Get the backup files
# ---------------------------------------------------------------
if [ "$FROM_R2" = true ]; then
    echo "Downloading from R2..."
    mkdir -p "$BACKUP_DIR"

    export RCLONE_CONFIG_R2_TYPE=s3
    export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
    export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY"
    export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_KEY"
    export RCLONE_CONFIG_R2_ENDPOINT="$R2_ENDPOINT"
    export RCLONE_CONFIG_R2_ACL=private

    if [ -n "$TARGET_DATE" ]; then
        rclone copy "r2:$R2_BUCKET/db/flowartswiki-db-$TARGET_DATE.sql.gz" "$BACKUP_DIR/"
        rclone copy "r2:$R2_BUCKET/xml/flowartswiki-xml-$TARGET_DATE.xml.gz" "$BACKUP_DIR/"
    else
        # Get the most recent files
        rclone copy "r2:$R2_BUCKET/db/" "$BACKUP_DIR/" --include "*.sql.gz" 2>/dev/null
        rclone copy "r2:$R2_BUCKET/xml/" "$BACKUP_DIR/" --include "*.xml.gz" 2>/dev/null
    fi
fi

# Find the target backup
if [ -n "$TARGET_DATE" ]; then
    SQL_FILE="$BACKUP_DIR/flowartswiki-db-$TARGET_DATE.sql.gz"
    XML_FILE="$BACKUP_DIR/flowartswiki-xml-$TARGET_DATE.xml.gz"
else
    SQL_FILE=$(ls -t "$BACKUP_DIR"/flowartswiki-db-*.sql.gz 2>/dev/null | head -1)
    XML_FILE=$(ls -t "$BACKUP_DIR"/flowartswiki-xml-*.xml.gz 2>/dev/null | head -1)
fi

if [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
    echo "ERROR: No SQL backup found."
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  (none)"
    exit 1
fi

echo "=== Restore Plan ==="
echo "  SQL: $SQL_FILE"
echo "  XML: ${XML_FILE:-not found (DB-only restore)}"
echo ""
read -p "This will OVERWRITE the current database. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# ---------------------------------------------------------------
# 2. Restore database
# ---------------------------------------------------------------
echo ""
echo "Restoring database..."

# Drop and recreate
docker compose exec -T db mariadb \
    --user=root \
    --password="$DB_ROOT_PASSWORD" \
    -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME;"

# Import dump
gunzip -c "$SQL_FILE" | docker compose exec -T db mariadb \
    --user=root \
    --password="$DB_ROOT_PASSWORD" \
    "$DB_NAME"

echo "  Database restored."

# ---------------------------------------------------------------
# 3. Restore XML content (if available)
# ---------------------------------------------------------------
if [ -n "$XML_FILE" ] && [ -f "$XML_FILE" ]; then
    echo "Importing XML content..."
    gunzip -c "$XML_FILE" | docker compose exec -T mediawiki \
        php maintenance/run.php importDump --no-updates /dev/stdin

    # Rebuild search index and links
    docker compose exec mediawiki php maintenance/run.php rebuildrecentchanges
    docker compose exec mediawiki php maintenance/run.php initSiteStats
    echo "  XML import complete."
fi

# ---------------------------------------------------------------
# 4. Run update script
# ---------------------------------------------------------------
echo "Running database updates..."
docker compose exec mediawiki php maintenance/run.php update --quick

# ---------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------
echo ""
echo "=== Verification ==="
PAGE_COUNT=$(docker compose exec -T mediawiki php maintenance/run.php showSiteStats 2>/dev/null | grep -i "total pages" || echo "unknown")
echo "  Pages: $PAGE_COUNT"
echo ""
echo "Restore complete. Visit https://flowartswiki.org to verify."
