"""SQLite persistence: which awards have been seen, so none is acted on twice."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from gcbot.models import AwardEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_awards (
    source        TEXT NOT NULL,
    award_key     TEXT NOT NULL,
    award_id      TEXT NOT NULL,
    recipient     TEXT NOT NULL,
    amount        TEXT NOT NULL,
    first_seen_ts TEXT NOT NULL,
    PRIMARY KEY (source, award_key)
);
"""


class StateStore:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def is_seen(self, event: AwardEvent) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_awards WHERE source = ? AND award_key = ?",
            (event.source, event.award_key),
        ).fetchone()
        return row is not None

    def mark_seen(self, event: AwardEvent, now: datetime | None = None) -> bool:
        """Record the award. Returns True if it was new, False if already seen."""
        ts = (now or datetime.now(timezone.utc)).isoformat()
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO seen_awards VALUES (?, ?, ?, ?, ?, ?)",
            (event.source, event.award_key, event.award_id, event.recipient_name,
             str(event.amount), ts),
        )
        self._conn.commit()
        return cur.rowcount == 1
