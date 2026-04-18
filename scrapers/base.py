import re
import requests
import logging
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

_WARM_RE = re.compile(r"warm|inkl\.?\s*nk|inkl\.?\s*nebenkosten|warmmiete", re.IGNORECASE)
_COLD_RE = re.compile(r"kalt|zzgl\.?\s*nk|zzgl\.?\s*nebenkosten|kaltmiete|k\.?\s*m\.", re.IGNORECASE)


def detect_rent_type(text: str) -> str:
    """Return 'warm', 'cold', or '' (unknown) based on free text."""
    if _WARM_RE.search(text):
        return "warm"
    if _COLD_RE.search(text):
        return "cold"
    return ""

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class Listing:
    id: str           # unique: "{source}_{internal_id}"
    title: str
    url: str
    source: str
    price: str = ""
    size: str = ""
    rooms: str = ""
    location: str = ""
    rent_type: str = ""  # "warm", "cold", or "" (unknown)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "price": self.price,
            "size": self.size,
            "rooms": self.rooms,
            "location": self.location,
            "rent_type": self.rent_type,
        }


class BaseScraper:
    SOURCE = "base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: str) -> Optional[str]:
        try:
            # polite delay between requests
            time.sleep(random.uniform(1.5, 3.5))
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError as e:
            code = e.response.status_code
            if code in (401, 403):
                logger.warning(
                    f"[{self.SOURCE}] HTTP {code} — site is blocking automated requests. "
                    "This scraper may require a headless browser to work."
                )
            else:
                logger.error(f"[{self.SOURCE}] HTTP {code} for {url}")
        except Exception as e:
            logger.error(f"[{self.SOURCE}] Failed to fetch {url}: {e}")
        return None

    def fetch(self, config: dict) -> List[Listing]:
        raise NotImplementedError
