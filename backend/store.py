import json
import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "watches.db"
_LOCK = threading.Lock()
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row


def init() -> None:
    with _LOCK:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL,
                checked_at REAL NOT NULL,
                min_price REAL,
                currency TEXT,
                priced_count INTEGER NOT NULL DEFAULT 0,
                total_count INTEGER NOT NULL DEFAULT 0,
                available INTEGER NOT NULL DEFAULT 0,
                providers TEXT,
                top_json TEXT,
                FOREIGN KEY (watch_id) REFERENCES watches (id) ON DELETE CASCADE
            );
            """
        )
        _conn.commit()


def add_watch(product: str, location: str) -> dict:
    with _LOCK:
        cur = _conn.execute(
            "INSERT INTO watches (product, location, created_at) VALUES (?, ?, ?)",
            (product.strip(), location.strip(), time.time()),
        )
        _conn.commit()
        row = _conn.execute("SELECT * FROM watches WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_watches() -> list[dict]:
    with _LOCK:
        rows = _conn.execute("SELECT * FROM watches ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_watch(watch_id: int) -> dict | None:
    with _LOCK:
        row = _conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    return dict(row) if row else None


def delete_watch(watch_id: int) -> None:
    with _LOCK:
        _conn.execute("DELETE FROM snapshots WHERE watch_id = ?", (watch_id,))
        _conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
        _conn.commit()


def add_snapshot(
    watch_id: int,
    min_price: float | None,
    currency: str | None,
    priced_count: int,
    total_count: int,
    available: bool,
    providers: list[str],
    top: list[dict],
) -> dict:
    with _LOCK:
        cur = _conn.execute(
            """
            INSERT INTO snapshots
                (watch_id, checked_at, min_price, currency, priced_count,
                 total_count, available, providers, top_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                watch_id,
                time.time(),
                min_price,
                currency,
                priced_count,
                total_count,
                1 if available else 0,
                ",".join(providers),
                json.dumps(top),
            ),
        )
        _conn.commit()
        row = _conn.execute("SELECT * FROM snapshots WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _hydrate(row)


def latest_snapshots(watch_id: int, limit: int = 2) -> list[dict]:
    with _LOCK:
        rows = _conn.execute(
            "SELECT * FROM snapshots WHERE watch_id = ? ORDER BY checked_at DESC LIMIT ?",
            (watch_id, limit),
        ).fetchall()
    return [_hydrate(r) for r in rows]


def history(watch_id: int, limit: int = 60) -> list[dict]:
    with _LOCK:
        rows = _conn.execute(
            "SELECT * FROM snapshots WHERE watch_id = ? ORDER BY checked_at DESC LIMIT ?",
            (watch_id, limit),
        ).fetchall()
    return [_hydrate(r) for r in rows]


def _hydrate(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["available"] = bool(data.get("available"))
    data["providers"] = data.get("providers", "").split(",") if data.get("providers") else []
    try:
        data["top"] = json.loads(data.pop("top_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        data["top"] = []
    return data
