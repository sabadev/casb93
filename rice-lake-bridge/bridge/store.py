"""Cola persistente en SQLite.

El ticket se guarda ANTES de intentar enviarlo: si el backend, la red o el
equipo se caen, el pesaje no se pierde y se reintenta al volver.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    uid           TEXT PRIMARY KEY,
    payload       TEXT NOT NULL,
    captured_at   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    attempts      INTEGER NOT NULL DEFAULT 0,
    next_retry_at REAL NOT NULL DEFAULT 0,
    last_error    TEXT,
    sent_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_tickets_pending
    ON tickets (status, next_retry_at);
"""


class Spool:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False + lock: la cola puede tocarse desde el loop
        # serie y desde un hilo de envio sin corromper la conexion.
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            str(self.path), isolation_level=None, check_same_thread=False
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> "Spool":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def enqueue(self, uid: str, payload: dict[str, Any], captured_at: str) -> bool:
        """Encola un ticket. False si el uid ya existia (duplicado)."""
        with self._lock:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO tickets (uid, payload, captured_at) VALUES (?,?,?)",
                (uid, json.dumps(payload, ensure_ascii=False), captured_at),
            )
        return cur.rowcount > 0

    def due(self, limit: int = 20, now: float | None = None) -> list[sqlite3.Row]:
        with self._lock:
            return list(
                self._db.execute(
                    "SELECT * FROM tickets WHERE status='pending' AND next_retry_at<=? "
                    "ORDER BY captured_at LIMIT ?",
                    (now if now is not None else time.time(), limit),
                )
            )

    def mark_sent(self, uid: str) -> None:
        with self._lock:
            self._db.execute(
                    "UPDATE tickets SET status='sent', sent_at=datetime('now'), last_error=NULL "
                "WHERE uid=?",
                (uid,),
            )

    def mark_failed(self, uid: str, error: str, retry_in_s: float) -> None:
        with self._lock:
            self._db.execute(
                    "UPDATE tickets SET attempts=attempts+1, last_error=?, next_retry_at=? "
                "WHERE uid=?",
                (error[:500], time.time() + retry_in_s, uid),
            )

    def mark_dead(self, uid: str, error: str) -> None:
        """Agota reintentos: queda para inspeccion manual, nunca se borra."""
        with self._lock:
            self._db.execute(
                    "UPDATE tickets SET status='dead', attempts=attempts+1, last_error=? WHERE uid=?",
                (error[:500], uid),
            )

    def counts(self) -> dict[str, int]:
        with self._lock:
            rows = self._db.execute(
                "SELECT status, COUNT(*) c FROM tickets GROUP BY status"
            ).fetchall()
        return {r["status"]: r["c"] for r in rows}

    def iter_all(self, status: str | None = None) -> Iterator[sqlite3.Row]:
        with self._lock:
            if status:
                rows = self._db.execute(
                    "SELECT * FROM tickets WHERE status=? ORDER BY captured_at", (status,)
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM tickets ORDER BY captured_at"
                ).fetchall()
        yield from rows


def backoff_seconds(attempts: int, base: float = 2.0, cap: float = 600.0) -> float:
    """Backoff exponencial acotado: 2s, 4s, 8s ... hasta 10 min."""
    return min(cap, base * (2 ** max(0, attempts)))
