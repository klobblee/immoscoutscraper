---
name: immoScoutScraper project
description: Python apartment listing monitor for Bochum, notifies via Telegram
type: project
---

Monitors Kleinanzeigen, Immowelt, and ImmobilienScout24 for apartment listings in Bochum and sends Telegram notifications.

**Why:** User wants automatic notifications for new listings matching their filters.

**How to apply:** When modifying scrapers, note that ImmobilienScout24 returns HTTP 401 (bot-blocked) and is currently disabled in effect. Kleinanzeigen uses `?maxPrice=N` query param (NOT `preis::N` path segment). Immowelt uses `a[data-testid="card-mfe-covering-link-testid"]` with title attribute for metadata.

**Stack:** Python + requests + BeautifulSoup + schedule + SQLite + Telegram Bot API (no library, plain requests POST).

**Run command (NixOS):**
`nix-shell -p python3Packages.requests python3Packages.beautifulsoup4 python3Packages.lxml python3Packages.pyyaml python3Packages.schedule --run "python3 main.py"`
