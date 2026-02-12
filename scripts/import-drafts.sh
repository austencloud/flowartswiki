#!/bin/bash
# Import wiki article drafts into MediaWiki via the API
# Usage: bash scripts/import-drafts.sh [optional: specific-file.wiki]
#
# Reads .wiki files from content/drafts/, derives page title from filename
# (underscores become spaces, .wiki extension stripped), and creates/updates
# the page via the MediaWiki API.

set -euo pipefail

WIKI_API="http://localhost:8080/api.php"
DRAFTS_DIR="F:/flow-arts-wiki/content/drafts"
COOKIE_JAR=$(mktemp)

# Read credentials from .env
source "F:/flow-arts-wiki/.env"
USERNAME="${MEDIAWIKI_ADMIN_USER}"
PASSWORD="${MEDIAWIKI_ADMIN_PASSWORD}"

cleanup() { rm -f "$COOKIE_JAR"; }
trap cleanup EXIT

echo "=== Flow Arts Wiki Draft Importer ==="
echo ""

# Step 1: Get login token
echo "Authenticating..."
LOGIN_TOKEN=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  "${WIKI_API}?action=query&meta=tokens&type=login&format=json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['query']['tokens']['logintoken'])" 2>/dev/null \
  || /c/Python313/python.exe -c "import sys,json; print(json.load(sys.stdin)['query']['tokens']['logintoken'])" <<< "$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" "${WIKI_API}?action=query&meta=tokens&type=login&format=json")")

# Step 2: Log in
LOGIN_RESULT=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -X POST "$WIKI_API" \
  -d "action=login&format=json" \
  --data-urlencode "lgname=${USERNAME}" \
  --data-urlencode "lgpassword=${PASSWORD}" \
  --data-urlencode "lgtoken=${LOGIN_TOKEN}")

LOGIN_STATUS=$(echo "$LOGIN_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('login',{}).get('result','FAIL'))" 2>/dev/null \
  || echo "$LOGIN_RESULT" | /c/Python313/python.exe -c "import sys,json; print(json.load(sys.stdin).get('login',{}).get('result','FAIL'))")

if [ "$LOGIN_STATUS" != "Success" ]; then
  echo "Login failed: $LOGIN_RESULT"
  exit 1
fi
echo "Logged in as ${USERNAME}"

# Step 3: Get CSRF token
CSRF_TOKEN=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  "${WIKI_API}?action=query&meta=tokens&format=json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['query']['tokens']['csrftoken'])" 2>/dev/null \
  || curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  "${WIKI_API}?action=query&meta=tokens&format=json" \
  | /c/Python313/python.exe -c "import sys,json; print(json.load(sys.stdin)['query']['tokens']['csrftoken'])")

echo "CSRF token acquired"
echo ""

# Step 4: Import files
SUCCESS=0
FAIL=0
SKIP=0

# Determine which files to import
if [ -n "${1:-}" ]; then
  FILES=("$DRAFTS_DIR/$1")
else
  FILES=("$DRAFTS_DIR"/*.wiki)
fi

TOTAL=${#FILES[@]}
echo "Importing ${TOTAL} articles..."
echo ""

for filepath in "${FILES[@]}"; do
  filename=$(basename "$filepath")

  # Skip non-article files (research docs, previews)
  if [[ "$filename" == *.md ]] || [[ "$filename" == "preview.html" ]]; then
    ((SKIP++))
    continue
  fi

  # Derive page title: remove .wiki extension, replace underscores with spaces
  title="${filename%.wiki}"
  title="${title//_/ }"

  # Read file content
  content=$(<"$filepath")

  # Skip empty files
  if [ -z "$content" ]; then
    echo "  SKIP (empty): $title"
    ((SKIP++))
    continue
  fi

  # Create/edit the page
  RESULT=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -X POST "$WIKI_API" \
    -d "action=edit&format=json" \
    --data-urlencode "title=${title}" \
    --data-urlencode "text=${content}" \
    --data-urlencode "token=${CSRF_TOKEN}" \
    --data-urlencode "summary=Import from content/drafts/${filename}" \
    -d "bot=1" \
    -d "createonly=0")

  # Check result
  EDIT_RESULT=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('edit',{}).get('result', r.get('error',{}).get('code','unknown')))" 2>/dev/null \
    || echo "$RESULT" | /c/Python313/python.exe -c "import sys,json; r=json.load(sys.stdin); print(r.get('edit',{}).get('result', r.get('error',{}).get('code','unknown')))")

  if [ "$EDIT_RESULT" = "Success" ]; then
    echo "  OK: $title"
    ((SUCCESS++))
  else
    echo "  FAIL: $title ($EDIT_RESULT)"
    ((FAIL++))
  fi
done

echo ""
echo "=== Done ==="
echo "  Success: ${SUCCESS}"
echo "  Failed:  ${FAIL}"
echo "  Skipped: ${SKIP}"
echo "  Total:   ${TOTAL}"
