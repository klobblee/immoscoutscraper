import requests
import logging

logger = logging.getLogger(__name__)


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def format_listing(listing: dict) -> str:
    lines = [f"🏠 <b>{listing['title']}</b>"]
    if listing.get("price"):
        lines.append(f"💰 {listing['price']}")
    if listing.get("size"):
        lines.append(f"📐 {listing['size']}")
    if listing.get("rooms"):
        lines.append(f"🛏 {listing['rooms']} Zi.")
    if listing.get("location"):
        lines.append(f"📍 {listing['location']}")
    lines.append(f"🔗 <a href=\"{listing['url']}\">Zur Anzeige →</a>")
    lines.append(f"<i>{listing['source']}</i>")
    return "\n".join(lines)
