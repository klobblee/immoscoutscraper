import json
import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from .base import BaseScraper, Listing, detect_rent_type

logger = logging.getLogger(__name__)


class ImmoscoutScraper(BaseScraper):
    SOURCE = "ImmobilienScout24"
    # Note: immoscout24.de redirects to immobilienscout24.de
    BASE_URL = "https://www.immobilienscout24.de"

    def build_url(self, cfg: dict) -> str:
        # URL format: /Suche/de/{state}/{city}/wohnung-mieten
        # state (Bundesland slug) must be configured — e.g. "nordrhein-westfalen"
        state = cfg.get("immoscout_state", "nordrhein-westfalen")
        city = cfg.get("city_slug") or cfg.get("city", "bochum").lower()
        params = []
        if cfg.get("max_rent"):
            params.append(f"price=-{int(cfg['max_rent'])}")
        if cfg.get("min_size_sqm"):
            params.append(f"livingspace={int(cfg['min_size_sqm'])}-")
        if cfg.get("min_rooms"):
            params.append(f"numberofrooms={cfg['min_rooms']}-")
        qs = "&".join(params)
        url = f"{self.BASE_URL}/Suche/de/{state}/{city}/wohnung-mieten"
        return f"{url}?{qs}" if qs else url

    def fetch(self, config: dict) -> List[Listing]:
        url = self.build_url(config)
        logger.info(f"[{self.SOURCE}] Fetching: {url}")
        html = self.fetch_page(url)
        if not html:
            return []

        # Check for bot detection wall (HTML-level)
        if "Ich bin kein Roboter" in html or "Robot Check" in html:
            logger.warning(
                f"[{self.SOURCE}] Bot detection triggered. "
                "ImmobilienScout24 requires a real browser (e.g. Playwright) to bypass. "
                "Skipping."
            )
            return []

        listings = self._parse_json(html)
        if listings:
            return listings

        logger.debug(f"[{self.SOURCE}] JSON parse failed, falling back to HTML")
        return self._parse_html(html)

    # ── JSON path ──────────────────────────────────────────────────────────────

    def _parse_json(self, html: str) -> List[Listing]:
        # ImmoScout24 embeds the result state in a script tag
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>',
            r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});\s*</script>',
        ]
        data = None
        for pattern in patterns:
            m = re.search(pattern, html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    break
                except json.JSONDecodeError:
                    continue

        if not data:
            # try <script id="is24-app-state"> or similar
            soup = BeautifulSoup(html, "lxml")
            for tag in soup.find_all("script", type="application/json"):
                try:
                    data = json.loads(tag.string)
                    if "searchResponse" in str(data) or "resultlist" in str(data):
                        break
                    data = None
                except (json.JSONDecodeError, TypeError):
                    continue

        if not data:
            return []

        return self._extract_from_state(data)

    def _extract_from_state(self, data: dict) -> List[Listing]:
        """Walk the state dict to find listing entries."""
        listings = []
        try:
            # Try common paths in the state object
            result_list = (
                data.get("searchResponse", {})
                    .get("resultlist", {})
                    .get("resultlistEntries", [{}])[0]
                    .get("resultlistEntry", [])
            )
            for entry in result_list:
                real_estate = (
                    entry.get("resultListEntry", {})
                        .get("realEstate", {})
                )
                listing_id = entry.get("@id") or real_estate.get("@id")
                if not listing_id:
                    continue

                title = real_estate.get("title", "Wohnung")
                price_obj = real_estate.get("price", {})
                price = (
                    f"{price_obj.get('value', '')} {price_obj.get('currency', 'EUR')}"
                    if price_obj else ""
                )
                size = real_estate.get("livingSpace", "")
                size_str = f"{size} m²" if size else ""
                rooms = real_estate.get("numberOfRooms", "")
                addr = real_estate.get("address", {})
                location = ", ".join(
                    filter(None, [addr.get("street"), addr.get("city")])
                )

                price_type = real_estate.get("price", {}).get("priceIntervalType", "")
                rent_type = detect_rent_type(price_type + " " + price)

                listings.append(Listing(
                    id=f"is24_{listing_id}",
                    title=title,
                    url=f"https://www.immobilienscout24.de/expose/{listing_id}",
                    source=self.SOURCE,
                    price=price,
                    size=size_str,
                    rooms=str(rooms),
                    location=location,
                    rent_type=rent_type,
                ))
        except Exception as e:
            logger.debug(f"[{self.SOURCE}] State extraction error: {e}")
        return listings

    # ── HTML fallback ──────────────────────────────────────────────────────────

    def _parse_html(self, html: str) -> List[Listing]:
        """
        Fallback: find all expose links in the page.
        ImmoScout24 renders listing cards server-side; each card contains
        a link to /expose/{id}.  If this breaks, inspect the page source
        and update the selectors here.
        """
        soup = BeautifulSoup(html, "lxml")
        seen_ids = set()
        listings = []

        for a_tag in soup.find_all("a", href=re.compile(r"/expose/(\d+)")):
            m = re.search(r"/expose/(\d+)", a_tag["href"])
            if not m:
                continue
            listing_id = m.group(1)
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)

            # Walk up the DOM to find the listing card container
            card = a_tag.find_parent(
                lambda t: t.name in ("li", "article", "div")
                and t.get("data-id") == listing_id
            ) or a_tag.find_parent(["li", "article"])

            title = a_tag.get_text(strip=True) or "Wohnung"
            price = size = rooms = location = ""

            if card:
                # Price: look for €
                price_tag = card.find(string=re.compile(r"€|\d+\s*€|\d+,\d+\s*€"))
                if price_tag:
                    price = price_tag.strip()

                # Size: look for m²
                size_tag = card.find(string=re.compile(r"\d+[\.,]?\d*\s*m²"))
                if size_tag:
                    size = size_tag.strip()

                # Rooms: look for Zi. or Zimmer
                room_tag = card.find(string=re.compile(r"\d[\.,]?\d*\s*Zi"))
                if room_tag:
                    rooms = room_tag.strip()

            listings.append(Listing(
                id=f"is24_{listing_id}",
                title=title,
                url=f"https://www.immobilienscout24.de/expose/{listing_id}",
                source=self.SOURCE,
                price=price,
                size=size,
                rooms=rooms,
                location=location,
                rent_type=detect_rent_type(price),
            ))

        logger.info(f"[{self.SOURCE}] HTML fallback found {len(listings)} listings")
        return listings
