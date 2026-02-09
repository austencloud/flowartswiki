# Flow Arts Wiki

Self-hosted MediaWiki instance for documenting flow arts knowledge. Runs on Docker with the Citizen skin, reverse-proxied by Caddy, backed up to Cloudflare R2.

## Architecture

```
[Cloudflare DNS/CDN] → [Hetzner VPS]
                           ├── Caddy (HTTPS, reverse proxy)
                           ├── MediaWiki 1.43 (PHP)
                           ├── MariaDB 11 (database)
                           └── Cron (daily backups → R2)
```

## Prerequisites

You need accounts on:

1. **Cloudflare** — register `flowarts.wiki`, manage DNS
2. **Hetzner Cloud** — provision a CX22 VPS (Ubuntu 24.04, ~$5/mo)
3. **Cloudflare R2** (optional) — backup storage (free tier = 10GB)

## Deployment

### 1. Provision VPS

Create a Hetzner CX22 server with Ubuntu 24.04. Add your SSH key.

### 2. Point DNS

In Cloudflare, add an A record:
- Name: `flowarts.wiki`
- Value: your Hetzner server IP
- Proxy: ON (orange cloud)

### 3. Deploy

SSH into your VPS and run:

```bash
curl -fsSL https://raw.githubusercontent.com/austencloud/flowartswiki/main/scripts/setup.sh | bash
```

Or manually:

```bash
git clone https://github.com/austencloud/flowartswiki.git /opt/flowartswiki
cd /opt/flowartswiki
bash scripts/setup.sh
```

The setup script will:
- Install Docker
- Configure the firewall (SSH + HTTP + HTTPS only)
- Harden SSH (key-only auth)
- Generate database passwords and secret keys
- Pull and start all containers
- Initialize the MediaWiki database
- Set up daily backup cron

### 4. Verify

Visit https://flowarts.wiki. You should see the wiki with the Citizen skin.

## Daily Operations

### Backups

Backups run automatically at 3:00 AM UTC via cron. Each backup produces:
- SQL dump (MariaDB database)
- XML export (portable MediaWiki content)

Both are compressed and uploaded to Cloudflare R2 (if configured). Local backups are retained for 30 days.

Manual backup:
```bash
cd /opt/flowartswiki
bash scripts/backup.sh
```

### Restore

```bash
# Restore latest local backup
bash scripts/restore.sh

# Restore specific date
bash scripts/restore.sh 2026-02-05_0300

# Download from R2 and restore
bash scripts/restore.sh --from-r2
```

### Updating MediaWiki

```bash
cd /opt/flowartswiki

# Pull new image
docker compose pull mediawiki

# Restart with new image
docker compose up -d

# Run database migrations
docker compose exec mediawiki php maintenance/run.php update --quick
```

### Logs

```bash
docker compose logs -f              # All containers
docker compose logs -f mediawiki    # MediaWiki only
docker compose logs -f caddy        # Caddy only
```

## Configuration

### Environment variables

Copy `.env.example` to `.env` and fill in values. Key variables:

| Variable | Purpose |
|----------|---------|
| `DB_PASSWORD` | MariaDB wiki user password |
| `DB_ROOT_PASSWORD` | MariaDB root password |
| `MEDIAWIKI_ADMIN_PASSWORD` | Wiki admin login |
| `MEDIAWIKI_SECRET_KEY` | Session signing key |
| `R2_*` | Cloudflare R2 backup credentials |

### MediaWiki settings

Edit `LocalSettings.php` for wiki behavior (permissions, extensions, branding).

### Skin theming

Edit `skins/citizen-overrides.css` for colors, typography, and layout adjustments.

## Extensions

| Extension | Purpose |
|-----------|---------|
| Citizen (skin) | Modern responsive layout |
| VisualEditor | WYSIWYG editing |
| Cite | `<ref>` footnotes |
| CiteThisPage | Citation sidebar link |
| CategoryTree | Hierarchical category browsing |
| ParserFunctions | Template logic |
| Scribunto | Lua-based templates (infoboxes) |
| ConfirmEdit | CAPTCHA on signup |
| AbuseFilter | Anti-vandalism rules |

## License

Wiki content is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Infrastructure code in this repository is MIT licensed.
