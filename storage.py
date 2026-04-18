import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "listings.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_listings (
            id TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def is_new(listing_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id FROM seen_listings WHERE id = ?", (listing_id,)
    ).fetchone()
    conn.close()
    return row is None


def mark_seen(listing_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO seen_listings (id, first_seen) VALUES (?, ?)",
        (listing_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
