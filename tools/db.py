"""Database utility for querying the SQLite financial database."""

import os
import sqlite3
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fraud.db")

def ensure_database():
    """Ensure the database exists and contains tables; if not, generate it."""
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        from data.generate_data import generate_synthetic_database
        generate_synthetic_database(DB_FILE)

def get_connection() -> sqlite3.Connection:
    ensure_database()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    rows = query_db(sql, params)
    return rows[0] if rows else None
