#!/usr/bin/env bash
set -euo pipefail

# Flow Arts Wiki - Daily Backup Script
# Dumps MariaDB + exports MediaWiki XML, uploads to Cloudflare R2.
# Run via cron or manually: bash scripts/backup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y-%m-%d_%H%M)
RETAIN_DAYS=30

cd "$PROJECT_DIR"
source .env

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# ---------------------------------------------------------------
# 1. MariaDB dump
# ---------------------------------------------------------------
SQL_FILE="$BACKUP_DIR/flowartswiki-db-$DATE.sql.gz"
echo "  Dumping database..."
docker compose exec -T db mariadb-dump \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    "$DB_NAME" | gzip > "$SQL_FILE"

SQL_SIZE=$(du -h "$SQL_FILE" | cut -f1)
echo "  Database dump: $SQL_FILE ($SQL_SIZE)"

# ---------------------------------------------------------------
# 2. MediaWiki XML export
# ---------------------------------------------------------------
XML_FILE="$BACKUP_DIR/flowartswiki-xml-$DATE.xml.gz"
echo "  Exporting wiki XML..."
docker compose exec -T mediawiki php maintenance/run.php dumpBackup \
    --full \
    --include-files \
    2>/dev/null | gzip > "$XML_FILE"

XML_SIZE=$(du -h "$XML_FILE" | cut -f1)
echo "  XML export: $XML_FILE ($XML_SIZE)"

# ---------------------------------------------------------------
# 3. Upload to Cloudflare R2 (if configured)
# ---------------------------------------------------------------
if [ -n "${R2_BUCKET:-}" ] && [ "$R2_BUCKET" != "flowartswiki-backups" ] || [ "${R2_ACCESS_KEY:-}" != "CHANGE_ME" ]; then
    echo "  Uploading to R2..."

    # Configure rclone on the fly (no persistent config needed)
    export RCLONE_CONFIG_R2_TYPE=s3
    export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
    export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY"
    export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_KEY"
    export RCLONE_CONFIG_R2_ENDPOINT="$R2_ENDPOINT"
    export RCLONE_CONFIG_R2_ACL=private

    rclone copy "$SQL_FILE" "r2:$R2_BUCKET/db/"
    rclone copy "$XML_FILE" "r2:$R2_BUCKET/xml/"

    echo "  Uploaded to R2 bucket: $R2_BUCKET"

    # Prune old remote backups
    rclone delete "r2:$R2_BUCKET/db/" --min-age "${RETAIN_DAYS}d" 2>/dev/null || true
    rclone delete "r2:$R2_BUCKET/xml/" --min-age "${RETAIN_DAYS}d" 2>/dev/null || true
else
    echo "  R2 not configured, keeping backups local only."
fi

# ---------------------------------------------------------------
# 4. Prune old local backups
# ---------------------------------------------------------------
echo "  Pruning local backups older than $RETAIN_DAYS days..."
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETAIN_DAYS -delete 2>/dev/null || true

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$(date)] Backup complete. Total local backup size: $TOTAL_SIZE"
