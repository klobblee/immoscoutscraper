import json
import re
import logging
from typing import List
from bs4 import BeautifulSoup
from .base import BaseScraper, Listing, detect_rent_type

logger = logging.getLogger(__name__)


class KleinanzeigenScraper(BaseScraper):
    SOURCE = "Kleinanzeigen"
    BASE_URL = "https://www.kleinanzeigen.de"

    def build_url(self, cfg: dict) -> str:
        city_slug = cfg.get("city_slug", "bochum")
        max_rent = cfg.get("max_rent", "")

        # Category c203 = Wohnungen mieten
        # Price filter goes as a query param (?maxPrice=N), NOT in the URL path
        base = f"{self.BASE_URL}/s-wohnung-mieten/{city_slug}/k0c203"
        if max_rent:
            return f"{base}?maxPrice={int(max_rent)}"
        return base

    def fetch(self, config: dict) -> List[Listing]:
        url = self.build_url(config)
        logger.info(f"[{self.SOURCE}] Fetching: {url}")
        html = self.fetch_page(url)
        if not html:
            return []
        return self._parse_html(html)

    def _parse_html(self, html: str) -> List[Listing]:
        """
        Kleinanzeigen renders each ad as:
          <article class="aditem" data-adid="12345" data-href="/s-anzeige/...">

        The title comes from a JSON-LD <script type="application/ld+json"> inside the article.
        Price is in an element whose class contains "price".
        Location is in an element whose class contains "top--left".
        Size/rooms are in the description snippet.

        If selectors break, open the search URL in a browser and inspect an article element.
        """
        soup = BeautifulSoup(html, "lxml")
        listings = []

        articles = soup.find_all("article", class_=re.compile(r"aditem"))
        if not articles:
            logger.warning(
                f"[{self.SOURCE}] No listing articles found — "
                "site structure may have changed."
            )
            return []

        for article in articles:
            # Skip promoted / top-ads
            if "aditem-topad" in " ".join(article.get("class", [])):
                continue

            listing_id = article.get("data-adid", "")
            if not listing_id:
                continue

            # Title from JSON-LD (most reliable)
            title = ""
            jld_tag = article.find("script", type="application/ld+json")
            if jld_tag and jld_tag.string:
                try:
                    jld = json.loads(jld_tag.string)
                    title = jld.get("title", "")
                except (json.JSONDecodeError, ValueError):
                    pass

            # Fallback title from link text
            if not title:
                link = article.find("a", href=re.compile(r"/s-anzeige/"))
                if link:
                    title = link.get_text(strip=True)
            if not title:
                title = "Wohnung"

            # URL — prefer data-href attribute on the article
            data_href = article.get("data-href", "")
            if data_href:
                url = self.BASE_URL + data_href
            else:
                link = article.find("a", href=re.compile(r"/s-anzeige/"))
                url = (self.BASE_URL + link["href"]) if link else ""

            # Price
            price = ""
            price_el = article.find(class_=lambda c: c and "price" in c)
            if price_el:
                price = price_el.get_text(strip=True)

            # Location (zip + district)
            location = ""
            loc_el = article.find(class_=lambda c: c and "top--left" in c)
            if loc_el:
                location = loc_el.get_text(strip=True)

            # Size & rooms from description snippet
            size = rooms = ""
            desc_el = article.find(class_=lambda c: c and "description" in c)
            if desc_el:
                text = desc_el.get_text()
                m_size = re.search(r"(\d+[\.,]?\d*)\s*m²", text)
                if m_size:
                    size = m_size.group(0)
                m_rooms = re.search(r"(\d[\.,]?\d*)\s*Zimmer", text, re.IGNORECASE)
                if m_rooms:
                    rooms = m_rooms.group(1)

            desc_text = desc_el.get_text() if desc_el else ""
            rent_type = detect_rent_type(price + " " + title + " " + desc_text)

            listings.append(Listing(
                id=f"ka_{listing_id}",
                title=title,
                url=url,
                source=self.SOURCE,
                price=price,
                size=size,
                rooms=rooms,
                location=location,
                rent_type=rent_type,
            ))

        logger.info(f"[{self.SOURCE}] Found {len(listings)} listings")
        return listings
