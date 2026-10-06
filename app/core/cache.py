"""Caché local de respuestas para no pagar dos veces por la misma consulta."""
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.db import Database


def cache_key(endpoint: str, payload: Any) -> str:
    raw = json.dumps({"e": endpoint, "p": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    response: dict
    cost: float | None
    created_at: float


class ResponseCache:
    def __init__(self, db: Database, enabled: bool = True):
        self.db = db
        self.enabled = enabled

    def get(self, endpoint: str, payload: Any) -> CacheEntry | None:
        if not self.enabled:
            return None
        rows = self.db.execute(
            "SELECT response, cost, created_at FROM cache WHERE key = ? AND expires_at > ?",
            (cache_key(endpoint, payload), time.time()),
        )
        if not rows:
            return None
        row = rows[0]
        return CacheEntry(json.loads(row["response"]), row["cost"], row["created_at"])

    def set(self, endpoint: str, payload: Any, response: dict, cost: float | None, ttl: int) -> None:
        if not self.enabled or ttl <= 0:
            return
        now = time.time()
        self.db.execute(
            "INSERT OR REPLACE INTO cache (key, endpoint, payload, response, cost, created_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                cache_key(endpoint, payload),
                endpoint,
                json.dumps(payload, ensure_ascii=False),
                json.dumps(response, ensure_ascii=False),
                cost,
                now,
                now + ttl,
            ),
        )

    def clear(self) -> int:
        rows = self.db.execute("SELECT COUNT(*) AS n FROM cache")
        self.db.execute("DELETE FROM cache")
        return rows[0]["n"]

    def purge_expired(self) -> None:
        self.db.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))
