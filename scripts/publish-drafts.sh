#!/bin/bash
# Publish all wiki drafts to MediaWiki via maintenance/edit.php
# Usage: bash scripts/publish-drafts.sh [--dry-run]
#
# Reads each .wiki file from content/drafts/ and creates/updates
# the corresponding MediaWiki page. Skips Template_ prefixed files
# (handled separately) and redirect files.

set -e

DRAFTS_DIR="content/drafts"
DRY_RUN=false
PUBLISHED=0
SKIPPED=0
FAILED=0

if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "=== DRY RUN - no pages will be created ==="
fi

echo "Publishing drafts from $DRAFTS_DIR..."
echo ""

for f in "$DRAFTS_DIR"/*.wiki; do
    [ -f "$f" ] || continue

    filename=$(basename "$f" .wiki)

    # Skip non-article files
    case "$filename" in
        research-*) echo "SKIP: $filename (not an article)"; SKIPPED=$((SKIPPED+1)); continue ;;
    esac

    # Convert filename to page title
    # Template_ prefix -> Template: namespace
    # Underscores -> spaces (MediaWiki handles both)
    if [[ "$filename" == Template_* ]]; then
        title="Template:${filename#Template_}"
        title=$(echo "$title" | sed 's/_/ /g')
    else
        title=$(echo "$filename" | sed 's/_/ /g')
        # Fix disambiguation parentheses: "Isolation (flow arts)" not "Isolation  (flow arts)"
        title=$(echo "$title" | sed 's/  / /g')
    fi

    echo -n "Publishing: $title ... "

    if [ "$DRY_RUN" = true ]; then
        echo "would publish ($(wc -l < "$f") lines)"
        PUBLISHED=$((PUBLISHED+1))
        continue
    fi

    # Publish via maintenance/edit.php
    if docker compose exec -T mediawiki php maintenance/run.php edit "$title" \
        --summary "Import from draft: AI-generated scaffold, pending human review" \
        --user "Austen" \
        < "$f" 2>/dev/null; then
        echo "OK"
        PUBLISHED=$((PUBLISHED+1))
    else
        echo "FAILED"
        FAILED=$((FAILED+1))
    fi
done

echo ""
echo "=== Results ==="
echo "Published: $PUBLISHED"
echo "Skipped: $SKIPPED"
echo "Failed: $FAILED"
