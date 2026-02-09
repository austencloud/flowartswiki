# Flow Arts Wiki - Claude Code Project Guide

## NPX Bug (Windows Git Bash)

**ALWAYS prefix npm/npx commands with `set +o onecmd;`** - otherwise output is lost.

```bash
# WRONG
npx some-tool
npm run build

# CORRECT
set +o onecmd; npx some-tool
set +o onecmd; npm run build
```

---

## Project Overview

**Flow Arts Wiki** is a self-hosted MediaWiki 1.43 site for documenting flow arts knowledge.

**Stack:** MediaWiki 1.43 (PHP) + MariaDB 11 + Caddy 2 (reverse proxy) + Docker Compose

**Domain:** `flowarts.wiki`

**Deployment:** Hetzner VPS, Cloudflare DNS/CDN, R2 backups

**License:** Content is CC BY-SA 4.0, infrastructure code is MIT

---

## Key Files

| File | Purpose |
|------|---------|
| `LocalSettings.php` | MediaWiki configuration (permissions, extensions, branding) |
| `docker-compose.yml` | Container orchestration (mediawiki, mariadb, caddy) |
| `docker-compose.override.yml` | Local dev overrides |
| `Caddyfile` | HTTPS, reverse proxy, security headers |
| `config/robots.txt` | Search engine crawl rules |
| `config/favicon.svg` | Site icon |
| `scripts/setup.sh` | VPS provisioning and initial deployment |
| `scripts/backup.sh` | Daily backup to R2 |
| `scripts/restore.sh` | Restore from backup |
| `content/` | Wiki article drafts (wikitext) |

---

## Dev Commands

```bash
# Start the stack
docker compose up -d

# View logs
docker compose logs -f              # All containers
docker compose logs -f mediawiki    # MediaWiki only
docker compose logs -f caddy        # Caddy only

# Run MediaWiki maintenance
docker compose exec mediawiki php maintenance/run.php update --quick
docker compose exec mediawiki php maintenance/run.php rebuildall

# PHP lint (validate LocalSettings.php)
docker compose exec mediawiki php -l LocalSettings.php

# Restart after config changes
docker compose restart mediawiki

# Manual backup
bash scripts/backup.sh

# Database shell
docker compose exec db mariadb -u wiki -p flowartswiki
```

---

## Writing Style for Wiki Content

**Encyclopedic, neutral tone.** This is a reference wiki, not a blog.

- Third person, present tense
- State facts, cite sources where possible
- No promotional language, no hype
- Run `/ai-bust` on any generated content before publishing
- Avoid AI-isms: no em dashes, no "delve", no "journey", no "tapestry"
- See the `/ai-bust` skill for the full detection pattern list

---

## Verification Methods

| Change Type | How to Verify |
|-------------|---------------|
| `LocalSettings.php` edits | `docker compose exec mediawiki php -l LocalSettings.php` |
| Content/articles | Visit the page in browser |
| Docker/infra changes | `docker compose ps` to check health |
| Caddy config | `docker compose restart caddy` + check logs |
| Extension additions | Check Special:Version page |

---

## Wiki Domain Context

### Props (Flow Art Implements)
- **Poi** - weighted balls on strings/chains
- **Staff** - long rod, single or double
- **Fans** - folding or rigid fan props
- **Hoops** - hula hoops for dance/flow
- **Rope dart** - weighted end on a rope
- **Levitation wand** - magnetically levitated rod
- **Dragon staff** - staff with radiating spokes
- **Contact juggling** - balls rolled on body/hands

### Technique Domains
- **Planes** - wall plane, wheel plane, floor plane
- **Timing** - same time, split time, quarter time
- **Direction** - same direction, opposite direction
- **Patterns** - flowers, extensions, wraps, isolations, stalls, tosses
- **Body movement** - turns, transitions, footwork

### Culture & Community
- Flow jams, fire spinning, LED performance
- Festivals (Flow Arts Institute, Fire Conclave, regional burns)
- Safety (fire safety, fuel types, spinning area requirements)
- History and origins of various props

### Notation Systems
- **TKA (The Kinetic Alphabet)** - positional notation for prop movement
- **Notation pages** use subpages: `Notation/TKA`, `Notation/Vulcan_Tech_Gospel`

---

## Content Areas

- **Articles** - main namespace wiki pages (wikitext)
- **Templates** - reusable components (`Template:Infobox_Prop`, `Template:Technique`)
- **Categories** - hierarchical taxonomy (`Category:Props`, `Category:Techniques`)
- **CSS** - Citizen skin overrides for styling
- **Extensions** - Cite, CategoryTree, ParserFunctions, Scribunto, VisualEditor, AbuseFilter
