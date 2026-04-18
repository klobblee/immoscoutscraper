import re
import logging
from typing import List
from bs4 import BeautifulSoup
from .base import BaseScraper, Listing, detect_rent_type

logger = logging.getLogger(__name__)

# title attr format: "Wohnung zur Miete - Bochum - 1.080 € - 2 Zimmer, 76,9 m², EG"
_TITLE_RE = re.compile(
    r"(?P<type>.+?)\s*-\s*.+?\s*-\s*(?P<price>[\d\.,]+\s*€)\s*-\s*(?P<details>.+)"
)
_ROOMS_RE = re.compile(r"([\d,\.]+)\s*Zimmer")
_SIZE_RE  = re.compile(r"([\d,\.]+\s*m²)")


class ImmoweltScraper(BaseScraper):
    SOURCE = "Immowelt"
    BASE_URL = "https://www.immowelt.de"

    def build_url(self, cfg: dict) -> str:
        city = cfg.get("city_slug") or cfg.get("city", "bochum").lower()
        params = []
        if cfg.get("min_size_sqm"):
            params.append(f"ami={int(cfg['min_size_sqm'])}")
        if cfg.get("max_rent"):
            params.append(f"pma={int(cfg['max_rent'])}")
        if cfg.get("min_rooms"):
            params.append(f"rn={int(cfg['min_rooms'])}")
        qs = "&".join(params)
        url = f"{self.BASE_URL}/liste/{city}/wohnungen/mieten"
        return f"{url}?{qs}" if qs else url

    def fetch(self, config: dict) -> List[Listing]:
        url = self.build_url(config)
        logger.info(f"[{self.SOURCE}] Fetching: {url}")
        html = self.fetch_page(url)
        if not html:
            return []
        return self._parse_html(html)

    def _parse_html(self, html: str) -> List[Listing]:
        """
        Immowelt renders a list of cards, each with a covering <a> link that has
        a 'title' attribute containing the price, rooms, size, and property type.
        The address is in a sibling element with data-testid="cardmfe-description-box-address".

        If this breaks, open the page source and look for:
          - <a data-testid="card-mfe-covering-link-testid">
          - The 'title' attribute on that link
          - An element with data-testid containing "address"
        """
        soup = BeautifulSoup(html, "lxml")
        listings = []
        seen = set()

        covering_links = soup.find_all(
            "a", attrs={"data-testid": "card-mfe-covering-link-testid"}
        )
        if not covering_links:
            logger.warning(
                f"[{self.SOURCE}] No listing cards found — site structure may have changed."
            )
            return []

        for a_tag in covering_links:
            href = a_tag.get("href", "")
            # Extract UUID from expose URL
            m = re.search(r"/expose/([A-Za-z0-9-]+)", href)
            if not m:
                continue
            listing_id = m.group(1)
            if listing_id in seen:
                continue
            seen.add(listing_id)

            # Parse the title attribute: "Type - City - Price - Rooms, Size, ..."
            title_attr = a_tag.get("title", "")
            price = size = rooms = prop_type = ""
            tm = _TITLE_RE.match(title_attr)
            if tm:
                prop_type = tm.group("type").strip()
                price = tm.group("price").strip()
                details = tm.group("details")
                rm = _ROOMS_RE.search(details)
                if rm:
                    rooms = rm.group(1)
                sm = _SIZE_RE.search(details)
                if sm:
                    size = sm.group(1)

            # Address from sibling element
            card = a_tag.find_parent("div", attrs={"data-testid": re.compile(r"classified-card")})
            location = ""
            if card:
                addr_el = card.find(attrs={"data-testid": "cardmfe-description-box-address"})
                if addr_el:
                    location = addr_el.get_text(strip=True)

            # Build a meaningful title from type + location
            display_title = f"{prop_type}: {location}" if location else (prop_type or "Wohnung")

            listings.append(Listing(
                id=f"iw_{listing_id}",
                title=display_title,
                url=href,
                source=self.SOURCE,
                price=price,
                size=size,
                rooms=rooms,
                location=location,
                rent_type=detect_rent_type(title_attr + " " + price),
            ))

        logger.info(f"[{self.SOURCE}] Found {len(listings)} listings")
        return listings
