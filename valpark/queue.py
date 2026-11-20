"""File d'événements locale (SQLite) avec seq persistant.

Le seq ne doit jamais être réutilisé, même après redémarrage : il vit dans une table
`meta` séparée des événements, donc il continue après vidage de la file.
ponytail: pas de taille max —Prototype, quelques jours hors réseau au plus.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class EventQueue:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )
        self.conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('last_seq', 0)")
        self.conn.commit()

    def next_seq(self) -> int:
        row = self.conn.execute(
            "UPDATE meta SET value = value + 1 WHERE key = 'last_seq' RETURNING value"
        ).fetchone()
        self.conn.commit()
        return int(row[0])

    def add(self, event_type: str, *, ts: str | None = None, time_source: str = "none", **fields) -> dict:
        event: dict = {"seq": self.next_seq(), "type": event_type}
        if ts:
            event["ts"] = ts
        event["timeSource"] = time_source
        event.update(fields)
        self.conn.execute(
            "INSERT INTO events(seq, payload) VALUES (?, ?)", (event["seq"], json.dumps(event))
        )
        self.conn.commit()
        return event

    def pending(self, limit: int = 200) -> list[dict]:
        rows = self.conn.execute(
            "SELECT payload FROM events ORDER BY seq LIMIT ?", (limit,)
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def remove(self, seqs: list[int]) -> None:
        if not seqs:
            return
        self.conn.executemany("DELETE FROM events WHERE seq = ?", [(seq,) for seq in seqs])
        self.conn.commit()

    def size(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
