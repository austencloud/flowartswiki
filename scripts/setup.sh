#!/usr/bin/env bash
set -euo pipefail

# Flow Arts Wiki - VPS Bootstrap Script
# Run on a fresh Hetzner CX22 (Ubuntu 24.04)
# Usage: bash setup.sh

REPO_URL="https://github.com/austencloud/flowartswiki.git"
INSTALL_DIR="/opt/flowartswiki"

echo "=== Flow Arts Wiki - VPS Setup ==="
echo ""

# ---------------------------------------------------------------
# 1. System updates
# ---------------------------------------------------------------
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl git ufw fail2ban

# ---------------------------------------------------------------
# 2. Firewall
# ---------------------------------------------------------------
echo "[2/8] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# ---------------------------------------------------------------
# 3. SSH hardening
# ---------------------------------------------------------------
echo "[3/8] Hardening SSH..."
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd

# ---------------------------------------------------------------
# 4. Install Docker
# ---------------------------------------------------------------
echo "[4/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "  Docker already installed, skipping."
fi

# ---------------------------------------------------------------
# 5. Clone repo
# ---------------------------------------------------------------
echo "[5/8] Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  $INSTALL_DIR already exists. Pulling latest..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ---------------------------------------------------------------
# 6. Configure environment
# ---------------------------------------------------------------
echo "[6/8] Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env

    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/^MEDIAWIKI_SECRET_KEY=.*/MEDIAWIKI_SECRET_KEY=$SECRET_KEY/" .env

    # Generate database passwords
    DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    DB_ROOT_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$DB_PASS/" .env
    sed -i "s/^DB_ROOT_PASSWORD=.*/DB_ROOT_PASSWORD=$DB_ROOT_PASS/" .env

    echo ""
    echo "  Generated database passwords and secret key."
    echo "  IMPORTANT: Edit .env to set MEDIAWIKI_ADMIN_PASSWORD"
    echo "  and R2 credentials (if using backups)."
    echo ""
    read -p "  Press Enter after editing .env (or Ctrl+C to abort)..."
else
    echo "  .env already exists, skipping."
fi

# ---------------------------------------------------------------
# 7. Install Citizen skin
# ---------------------------------------------------------------
echo "[7/8] Installing Citizen skin..."
CITIZEN_DIR="$INSTALL_DIR/citizen-skin-repo"
if [ ! -d "$CITIZEN_DIR" ]; then
    git clone --depth 1 https://github.com/StarCitizenTools/mediawiki-skins-Citizen.git "$CITIZEN_DIR"
fi

# ---------------------------------------------------------------
# 8. Launch
# ---------------------------------------------------------------
echo "[8/8] Starting containers..."

# Copy Citizen skin into a named volume
docker volume create flowartswiki_citizen-skin 2>/dev/null || true
docker run --rm \
    -v "$CITIZEN_DIR:/src:ro" \
    -v flowartswiki_citizen-skin:/dest \
    alpine sh -c "cp -a /src/. /dest/"

# Copy the CSS override into the skin volume
docker run --rm \
    -v "$INSTALL_DIR/skins/citizen-overrides.css:/src/custom.css:ro" \
    -v flowartswiki_citizen-skin:/dest \
    alpine sh -c "cp /src/custom.css /dest/resources/skins.citizen.styles/custom.css 2>/dev/null || true"

docker compose up -d

echo ""
echo "  Waiting for containers to be healthy..."
sleep 15

# ---------------------------------------------------------------
# Run MediaWiki install (creates tables + admin account)
# ---------------------------------------------------------------
echo "  Running MediaWiki database setup..."

# Source .env for admin credentials
source .env

docker compose exec mediawiki php maintenance/run.php install \
    --dbserver=db \
    --dbname="$DB_NAME" \
    --dbuser="$DB_USER" \
    --dbpass="$DB_PASSWORD" \
    --pass="$MEDIAWIKI_ADMIN_PASSWORD" \
    --scriptpath="" \
    --server="https://flowarts.wiki" \
    "Flow Arts Wiki" \
    "$MEDIAWIKI_ADMIN_USER" \
    2>/dev/null || echo "  (Database may already be initialized)"

# Run any pending updates
docker compose exec mediawiki php maintenance/run.php update --quick 2>/dev/null || true

# ---------------------------------------------------------------
# Set up daily backup cron
# ---------------------------------------------------------------
echo "  Setting up daily backup cron..."
CRON_LINE="0 3 * * * cd $INSTALL_DIR && bash scripts/backup.sh >> /var/log/flowartswiki-backup.log 2>&1"
(crontab -l 2>/dev/null | grep -v flowartswiki; echo "$CRON_LINE") | crontab -

echo ""
echo "============================================"
echo "  Flow Arts Wiki is running!"
echo ""
echo "  URL: https://flowarts.wiki"
echo "  Admin: $MEDIAWIKI_ADMIN_USER"
echo ""
echo "  Backups: daily at 3:00 AM UTC"
echo "  Logs: docker compose logs -f"
echo "============================================"
