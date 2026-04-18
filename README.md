# immoScoutScraper

Small apartment monitor for German rental listings. It checks multiple sites, filters results, stores already-seen listings in SQLite, and sends new matches to Telegram.

Currently supported sites:
- ImmobilienScout24
- Kleinanzeigen
- Immowelt

## What it does

The script:
- loads search settings from `config.yaml`
- fetches listings from enabled sites
- filters by city, rent, size, rooms, and warm-rent preference
- skips listings that were already seen before
- sends new matches to Telegram

Seen listings are stored locally in `listings.db`.

## Project files

- `main.py`: entry point
- `config.example.yaml`: safe template without secrets, rename or copy this to `config.yaml`
- `config.yaml`: your real local config with Telegram credentials
- `listings.db`: local SQLite database of seen listings
- `scrapers/`: site-specific scrapers
- `notifier.py`: Telegram message sending and formatting
- `storage.py`: SQLite persistence

## Requirements

- Python 3.10+
- Internet access
- A Telegram bot token
- Your Telegram chat ID

Python packages:
- `requests`
- `beautifulsoup4`
- `lxml`
- `PyYAML`
- `schedule`

Install them with:

```bash
pip install -r requirements.txt
```

## Setup

1. Go into the project directory:

```bash
cd /home/zeus/documents/immoScoutScraper
```

2. Rename or copy the example config to create your real local config:

```bash
cp config.example.yaml config.yaml
```

Or rename it:

```bash
mv config.example.yaml config.yaml
```

Use `cp` if you want to keep the example template in the project. Use `mv` if you only need a single local config file.

3. Edit `config.yaml`.

Fill in:
- `telegram.bot_token`
- `telegram.chat_id`

Adjust the search parameters:
- `search.city`
- `search.city_slug`
- `search.immoscout_state`
- `search.max_rent`
- `search.min_size_sqm`
- `search.min_rooms`
- `search.warmmiete_only`

Example:

```yaml
telegram:
  bot_token: "123456:your_bot_token"
  chat_id: "123456789"

search:
  city: "Berlin"
  city_slug: "berlin"
  immoscout_state: "berlin"
  warmmiete_only: true
  max_rent: 1200
  min_size_sqm: 45
  min_rooms: 2.0
```

## Choosing the right city values

These three fields matter:

- `city`: display/filter name, for example `Berlin`
- `city_slug`: lowercase URL slug, for example `berlin`
- `immoscout_state`: Bundesland slug for ImmobilienScout24 URLs

Examples for `immoscout_state`:
- `berlin`
- `hamburg`
- `bayern`
- `hessen`
- `nordrhein-westfalen`

For most cities:
- `city_slug` is the lowercase city name used in the target site URL
- `immoscout_state` is the state the city belongs to

Example for Munich:

```yaml
city: "Muenchen"
city_slug: "muenchen"
immoscout_state: "bayern"
```

If a site uses a different slug than expected, open the city search page in your browser and copy the slug from the URL.

## Running the scraper

Run once:

```bash
python main.py --once
```

Run once without sending Telegram messages:

```bash
python main.py --once --dry-run
```

Run continuously on the configured interval:

```bash
python main.py
```

Use a custom config path:

```bash
python main.py --config config.yaml --once
```

## First test

Recommended first run:

```bash
python main.py --once --dry-run
```

This verifies that:
- dependencies are installed
- your config loads correctly
- the search URLs work
- parsing still works for the enabled sites

After that, run:

```bash
python main.py --once
```

If Telegram is configured correctly, new matching listings will be sent to your chat.

## How duplicates are handled

The project stores every sent listing ID in `listings.db`.

That means:
- the same listing is only sent once
- deleting `listings.db` resets the seen-history

If you want a fresh test from scratch:

```bash
rm listings.db
```

Only do that if you intentionally want to resend old matches.

## Site limitations

Some sites may block automated requests or change their HTML structure.

Current behavior:
- ImmobilienScout24 may trigger bot detection and return no results
- HTML selectors on any site can break if the site changes

If that happens, the script will usually log warnings instead of crashing the whole run.

## Troubleshooting

`Telegram bot_token not configured`

- You are still using the placeholder value in `config.yaml`.

`Failed to fetch` or HTTP 403/401

- The target site is blocking automated requests.
- Retry later or update the scraper.

`No listing cards found`

- The site structure probably changed.
- Inspect the site HTML and update the selectors in the matching scraper under `scrapers/`.

`No new listings found`

- This can be normal.
- It can also mean all current matches were already stored in `listings.db`.

## Security

- Do not commit your real `config.yaml` if it contains Telegram secrets.
- Share `config.example.yaml` instead.
- Rotate the Telegram token immediately if it was ever exposed.

## Suggested ignore rules

If you use git for this folder, add these entries to `.gitignore`:

```gitignore
config.yaml
listings.db
__pycache__/
```
