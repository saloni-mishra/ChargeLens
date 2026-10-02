import sqlite3

from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

DB_PATH = "ChargeLens.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(total_budget: int = 250):
    with db() as conn:
        # 1. Quota Tracker
        conn.execute("""
            CREATE TABLE IF NOT EXISTS serpapi_budget (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                searches_used INTEGER DEFAULT 0,
                billing_cycle_month TEXT NOT NULL
            )
        """)

        current_month = datetime.now().strftime("%Y-%m")

        conn.execute("""
            INSERT OR IGNORE INTO serpapi_budget
            (id, searches_used, billing_cycle_month)
            VALUES (1, 0, ?)
        """, (current_month,))

        # 2. Audit Trail
        conn.execute("""
            CREATE TABLE IF NOT EXISTS serpapi_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_type TEXT NOT NULL,
                query TEXT NOT NULL,
                status TEXT NOT NULL,
                http_code INTEGER,
                error_message TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # 3. Identity Resolution Cache
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identity_cache (
                raw_token TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Pricing Evidence Cache with TTL
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pricing_cache (
                canonical_name TEXT PRIMARY KEY,
                query_used TEXT NOT NULL,
                trimmed_snippets TEXT NOT NULL,
                extracted_json TEXT NOT NULL,
                retrieved_at TEXT NOT NULL
            )
        """)


def get_cached_pricing(
    canonical_name: str,
    ttl_days: int = 14
) -> Optional[Dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT query_used, trimmed_snippets, extracted_json, retrieved_at
            FROM pricing_cache
            WHERE canonical_name = ?
            """,
            (canonical_name,)
        ).fetchone()

        if not row:
            return None

        retrieved_at = datetime.fromisoformat(row["retrieved_at"])

        if datetime.now() - retrieved_at > timedelta(days=ttl_days):
            return None

        return dict(row)


def save_pricing_cache(
    canonical_name: str,
    query: str,
    snippets: str,
    extracted_json: str
):
    with db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO pricing_cache
            (canonical_name, query_used, trimmed_snippets, extracted_json, retrieved_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            canonical_name,
            query,
            snippets,
            extracted_json,
            datetime.now().isoformat()
        ))