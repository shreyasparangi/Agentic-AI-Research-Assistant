"""
SQLite Cache Manager
====================
Provides a lightweight local cache for scraped web content. The cache stores
extracted text by URL so repeated scraper runs can avoid redundant HTTP fetches.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

CACHE_DB_PATH = Path(__file__).resolve().parent / "scraper_cache.db"


def initialize_cache() -> None:
    """Create the scraper cache database and table if they do not already exist."""
    with sqlite3.connect(CACHE_DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scraper_cache (
                url TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
            """
        )
        connection.commit()


def get_cached_content(url: str, max_age_hours: int = 24) -> str | None:
    """
    Return cached scraper content if it exists and is newer than max_age_hours.
    """
    initialize_cache()

    with sqlite3.connect(CACHE_DB_PATH) as connection:
        row = connection.execute(
            "SELECT content, timestamp FROM scraper_cache WHERE url = ?",
            (url,),
        ).fetchone()

    if not row:
        return None

    content, timestamp = row
    cached_at = datetime.fromisoformat(timestamp)
    expires_at = cached_at + timedelta(hours=max_age_hours)

    if expires_at < datetime.now(timezone.utc):
        return None

    return content


def save_to_cache(url: str, content: str) -> None:
    """Insert or update scraped content for a URL."""
    initialize_cache()

    with sqlite3.connect(CACHE_DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO scraper_cache (url, content, timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                content = excluded.content,
                timestamp = excluded.timestamp
            """,
            (url, content, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()


initialize_cache()
