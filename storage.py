import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), "market_watcher.db")

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  fetched_at INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_url ON snapshots(url);
CREATE INDEX IF NOT EXISTS idx_snapshots_fetched ON snapshots(fetched_at);

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at INTEGER NOT NULL,
  content TEXT NOT NULL
);
"""

@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

with _conn() as c:
    c.executescript(SCHEMA)

def upsert_snapshots(pages: List[Dict]) -> None:
    with _conn() as c:
        c.executemany(
            "INSERT INTO snapshots (url, fetched_at, content_hash, text) VALUES (?, ?, ?, ?)",
            [(p["url"], p["fetched_at"], p["hash"], p["text"]) for p in pages]
        )

def get_last_snapshots(urls: List[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    with _conn() as c:
        for url in urls:
            row = c.execute(
                "SELECT text FROM snapshots WHERE url = ? ORDER BY fetched_at DESC LIMIT 1",
                (url,)
            ).fetchone()
            result[url] = row[0] if row else ""
    return result

def save_report(created_at: int, content: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO reports (created_at, content) VALUES (?, ?)",
            (created_at, content)
        )
