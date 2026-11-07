"""Share-link storage: one `arrangements` table keyed by content id.

The id is the first 128 bits of SHA-256 over the canonical JSON (sorted keys,
compact separators), base64url without padding: 22 characters. The same
arrangement always gets the same id, so a save is idempotent.

Both stores are synchronous and are called from FastAPI's threadpool (plain
`def` routes). Postgres opens one short connection per call: saves are capped
at 10 a minute per address, and a fresh connection survives Neon's idle
autosuspend, which a held connection would not.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
import threading
from typing import Any, Protocol

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{22}$")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text. Raises `ValueError` on NaN or infinity."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def arrangement_id(canonical: str) -> str:
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()[:16]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class Store(Protocol):
    def init(self) -> None:
        """Create the table if it is missing."""
        ...

    def put(self, id: str, canonical: str) -> None:
        """Store `canonical` under `id`; a repeat is a no-op."""
        ...

    def get(self, id: str) -> str | None:
        """The canonical JSON text, or None."""
        ...

    def close(self) -> None: ...


class SqliteStore:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()

    def init(self) -> None:
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS arrangements ("
                "id TEXT PRIMARY KEY, json TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')))"
            )

    def put(self, id: str, canonical: str) -> None:
        with self._lock, self._db:
            self._db.execute("INSERT OR IGNORE INTO arrangements (id, json) VALUES (?, ?)", (id, canonical))

    def get(self, id: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT json FROM arrangements WHERE id = ?", (id,)).fetchone()
        return None if row is None else row[0]

    def close(self) -> None:
        with self._lock:
            self._db.close()


class PostgresStore:
    def __init__(self, url: str) -> None:
        self._url = url

    def _connect(self):
        import psycopg

        return psycopg.connect(self._url, autocommit=True, connect_timeout=5)

    def init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS arrangements ("
                "id TEXT PRIMARY KEY, json TEXT NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )

    def put(self, id: str, canonical: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO arrangements (id, json) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (id, canonical),
            )

    def get(self, id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT json FROM arrangements WHERE id = %s", (id,)).fetchone()
        return None if row is None else row[0]

    def close(self) -> None:
        pass


def store_from_env(env: dict[str, str], default_sqlite: str = "./studio.sqlite3") -> Store:
    """Postgres when `DATABASE_URL` is set, else SQLite at `PEWPEW_STUDIO_DB`."""
    url = env.get("DATABASE_URL")
    if url:
        return PostgresStore(url)
    return SqliteStore(env.get("PEWPEW_STUDIO_DB", default_sqlite))
