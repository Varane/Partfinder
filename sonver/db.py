import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable

DB_FILE = Path(__file__).resolve().parent / "sonver.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            article TEXT,
            brand TEXT,
            model TEXT,
            description TEXT,
            price REAL,
            currency TEXT,
            location TEXT,
            url TEXT,
            image_url TEXT,
            last_seen TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_article ON parts(article)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_platform ON parts(platform)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_price ON parts(price)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_item ON parts(platform, article, url)")
    conn.commit()
    conn.close()


def _execute(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> None:
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()


def upsert_part(item: Dict[str, Any]) -> bool:
    """Insert or update a part. Returns True when inserted, False when updated."""

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM parts WHERE platform = ? AND article = ? AND url = ?",
        (item.get("platform"), item.get("article"), item.get("url")),
    )
    existing = cur.fetchone()

    if existing:
        _execute(
            conn,
            """
            UPDATE parts
            SET brand = ?, model = ?, description = ?, price = ?, currency = ?,
                location = ?, image_url = ?, last_seen = ?
            WHERE id = ?
            """,
            (
                item.get("brand"),
                item.get("model"),
                item.get("description"),
                item.get("price"),
                item.get("currency"),
                item.get("location"),
                item.get("image_url"),
                item.get("last_seen"),
                existing["id"],
            ),
        )
        conn.close()
        return False

    _execute(
        conn,
        """
        INSERT INTO parts (
            platform, article, brand, model, description, price, currency,
            location, url, image_url, last_seen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.get("platform"),
            item.get("article"),
            item.get("brand"),
            item.get("model"),
            item.get("description"),
            item.get("price"),
            item.get("currency"),
            item.get("location"),
            item.get("url"),
            item.get("image_url"),
            item.get("last_seen"),
        ),
    )
    conn.close()
    return True
