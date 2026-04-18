#!/usr/bin/env python3
"""
Apartment listing monitor for Bochum (ImmobilienScout24, Kleinanzeigen, Immowelt).
Sends new listings to Telegram.

Usage:
    python main.py                  # run once then loop on schedule
    python main.py --once           # single scan and exit
    python main.py --dry-run        # scan but do NOT send Telegram messages
"""

import argparse
import logging
import re
import sys
import time

import schedule
import yaml

import storage
from notifier import format_listing, send_telegram
from scrapers import ImmoscoutScraper, KleinanzeigenScraper, ImmoweltScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRAPERS = {
    "immoscout24": ImmoscoutScraper,
    "kleinanzeigen": KleinanzeigenScraper,
    "immowelt": ImmoweltScraper,
}


def parse_price(price_str: str) -> float | None:
    """Extract a numeric rent value from a price string like '1.080 €' or '700 EUR'."""
    if not price_str:
        return None
    # Remove thousand separators (dots before 3 digits) and normalise decimal comma
    cleaned = re.sub(r'\.(?=\d{3})', '', price_str)
    cleaned = cleaned.replace(',', '.')
    m = re.search(r'[\d]+(?:\.\d+)?', cleaned)
    return float(m.group()) if m else None


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_scan(config: dict, dry_run: bool = False):
    search_cfg = config.get("search", {})
    tg_cfg = config.get("telegram", {})
    sites_cfg = config.get("sites", {})

    new_count = 0

    for site_key, scraper_cls in SCRAPERS.items():
        if not sites_cfg.get(site_key, True):
            continue

        scraper = scraper_cls()
        try:
            listings = scraper.fetch(search_cfg)
        except Exception as e:
            logger.error(f"[{site_key}] Scraper crashed: {e}")
            continue

        city_filter = search_cfg.get("city", "").lower()
        warmmiete_only = search_cfg.get("warmmiete_only", False)
        max_rent = search_cfg.get("max_rent")
        min_size = search_cfg.get("min_size_sqm")
        min_rooms = search_cfg.get("min_rooms")
        for listing in listings:
            if city_filter and listing.location:
                if city_filter not in listing.location.lower():
                    logger.debug(f"Skipping non-{search_cfg['city']} listing: {listing.location}")
                    continue

            if warmmiete_only and listing.rent_type == "cold":
                logger.debug(f"Skipping cold-rent listing: {listing.title}")
                continue

            price_val = parse_price(listing.price)
            if max_rent and price_val and price_val > max_rent:
                logger.debug(f"Skipping over-budget listing ({price_val}€): {listing.title}")
                continue

            if not storage.is_new(listing.id):
                continue

            new_count += 1
            msg = format_listing(listing.to_dict())
            logger.info(f"NEW listing: {listing.title} ({listing.source})")

            if dry_run:
                print("\n--- DRY RUN ---")
                print(msg)
                print("---------------\n")
            else:
                sent = send_telegram(
                    tg_cfg["bot_token"],
                    tg_cfg["chat_id"],
                    msg,
                )
                if not sent:
                    logger.warning(f"Failed to send Telegram message for {listing.id}")

            storage.mark_seen(listing.id)

    if new_count == 0:
        logger.info("No new listings found.")
    else:
        logger.info(f"Scan complete — {new_count} new listing(s) sent.")


def main():
    parser = argparse.ArgumentParser(description="Apartment listing monitor")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print to stdout instead of sending Telegram messages")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    config = load_config(args.config)

    # Validate Telegram config (unless dry-run)
    if not args.dry_run:
        tg = config.get("telegram", {})
        if tg.get("bot_token") == "YOUR_BOT_TOKEN_HERE":
            logger.error(
                "Telegram bot_token not configured. "
                "Edit config.yaml or use --dry-run to test without Telegram."
            )
            sys.exit(1)

    storage.init_db()

    interval = config.get("interval_minutes", 15)

    if args.once:
        run_scan(config, dry_run=args.dry_run)
        return

    # Run immediately, then on schedule
    logger.info(f"Starting monitor — scanning every {interval} minute(s). Press Ctrl+C to stop.")
    run_scan(config, dry_run=args.dry_run)

    schedule.every(interval).minutes.do(run_scan, config=config, dry_run=args.dry_run)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopped.")


if __name__ == "__main__":
    main()
