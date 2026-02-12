#!/usr/bin/env bash
# One-time setup for local MediaWiki development.
# Downloads MediaWiki, creates a SQLite database, and configures for local dev.
#
# Prerequisites: PHP 8.1+ with sqlite3, mbstring, xml, intl extensions
# Install PHP: scoop install php  -or-  choco install php
#
# Usage: bash scripts/dev-setup.sh

set -euo pipefail

WIKI_DIR="wiki"
MW_VERSION="1.43.0"
MW_URL="https://releases.wikimedia.org/mediawiki/1.43/mediawiki-${MW_VERSION}.tar.gz"

# Check PHP
if ! command -v php &> /dev/null; then
    echo "PHP not found. Install it first:"
    echo "  scoop install php"
    echo "  -or-"
    echo "  choco install php"
    exit 1
fi

echo "PHP found: $(php -v | head -1)"

# Check required extensions
MISSING=()
for ext in sqlite3 mbstring xml intl; do
    if ! php -m 2>/dev/null | grep -qi "^${ext}$"; then
        MISSING+=("$ext")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "Missing PHP extensions: ${MISSING[*]}"
    echo "Enable them in your php.ini by uncommenting:"
    for ext in "${MISSING[@]}"; do
        echo "  extension=${ext}"
    done
    echo ""
    echo "Find your php.ini: php --ini"
    exit 1
fi

# Download MediaWiki
if [ ! -d "$WIKI_DIR" ]; then
    echo "Downloading MediaWiki ${MW_VERSION}..."
    curl -L "$MW_URL" -o mediawiki.tar.gz
    mkdir -p "$WIKI_DIR"
    tar -xzf mediawiki.tar.gz --strip-components=1 -C "$WIKI_DIR"
    rm mediawiki.tar.gz
    echo "Extracted to ${WIKI_DIR}/"
else
    echo "MediaWiki directory already exists, skipping download."
fi

# Copy router script
cp scripts/dev-router.php "$WIKI_DIR/router.php"

# Copy branding assets
[ -f config/favicon.svg ] && cp config/favicon.svg "$WIKI_DIR/favicon.svg"
[ -f config/robots.txt ] && cp config/robots.txt "$WIKI_DIR/robots.txt"

# Copy custom extensions
if [ -d "extensions/LinkHealth" ]; then
    cp -r extensions/LinkHealth "$WIKI_DIR/extensions/LinkHealth"
fi

# Create SQLite data directory
mkdir -p "$WIKI_DIR/data"

# Install MediaWiki with SQLite
if [ ! -f "$WIKI_DIR/data/flowartswiki.sqlite" ]; then
    echo "Installing MediaWiki with SQLite..."
    php "$WIKI_DIR/maintenance/install.php" \
        --dbtype=sqlite \
        --dbpath="$(cd "$WIKI_DIR/data" && pwd)" \
        --server="http://localhost:8080" \
        --scriptpath="" \
        --pass=flowartswikidev \
        "Flow Arts Wiki" \
        "Admin"
    echo "Database created."
else
    echo "Database already exists, skipping install."
fi

# Overwrite generated LocalSettings with our dev config
cp LocalSettings.dev.php "$WIKI_DIR/LocalSettings.php"

echo ""
echo "========================================="
echo "  Setup complete!"
echo "========================================="
echo ""
echo "  Press F5 in VS Code to start, or run:"
echo "    php -S localhost:8080 -t wiki wiki/router.php"
echo ""
echo "  Open: http://localhost:8080/wiki/Main_Page"
echo "  Login: Admin / flowartswikidev"
echo ""
