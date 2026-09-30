"""SQLite storage. One connection shared across threads behind a lock."""
import sqlite3
import threading

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS nets (id INTEGER PRIMARY KEY, name TEXT, opened REAL, closed REAL);
CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY, net_id INTEGER, ts REAL, call TEXT, name TEXT, location TEXT,
  class TEXT, valid INTEGER, first_time INTEGER, flags TEXT, recheck_done INTEGER DEFAULT 0,
  transcript TEXT, UNIQUE(net_id, call));
CREATE TABLE IF NOT EXISTS transmissions (
  id INTEGER PRIMARY KEY, net_id INTEGER, ts REAL, seconds REAL, text TEXT, calls TEXT);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, pw_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'operator')), created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created REAL NOT NULL, expires REAL NOT NULL);
"""

_lock = threading.Lock()
_conn = None


def connect(path=None):
    """Open (or reopen, for tests) the database and create tables."""
    global _conn
    path = path or config.DB_PATH
    if str(path) != ":memory:":
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA foreign_keys = ON")
    _conn.executescript(SCHEMA)
    _migrate(_conn)
    return _conn


def _migrate(conn):
    """Add columns introduced after 1.0.0 to existing databases."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, kind in [("callsign", "TEXT"), ("license_name", "TEXT"), ("license_class", "TEXT"),
                      ("license_verified", "REAL"), ("verified_by", "TEXT")]:
        if col not in have:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {kind}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_callsign ON users(callsign) WHERE callsign IS NOT NULL")
    conn.commit()


def q(sql, args=(), one=False):
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        rows = [dict(r) for r in cur.fetchall()]
    return (rows[0] if rows else None) if one else rows


def insert(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur.lastrowid
