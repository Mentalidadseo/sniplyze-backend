"""Base de datos SQLite local: caché de respuestas, registro de costes y rastreos."""
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    endpoint   TEXT NOT NULL,
    payload    TEXT NOT NULL,
    response   TEXT NOT NULL,
    cost       REAL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS api_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    endpoint    TEXT NOT NULL,
    units       REAL NOT NULL DEFAULT 1,
    cost        REAL,
    from_cache  INTEGER NOT NULL DEFAULT 0,
    status_code INTEGER,
    ok          INTEGER NOT NULL DEFAULT 1,
    message     TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_calls_endpoint ON api_calls(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_calls_ts ON api_calls(ts);
CREATE TABLE IF NOT EXISTS crawls (
    task_id         TEXT PRIMARY KEY,
    target          TEXT NOT NULL,
    max_crawl_pages INTEGER NOT NULL,
    options         TEXT NOT NULL,
    created_at      REAL NOT NULL
);
"""


class Database:
    """Conexión SQLite compartida entre hilos (FastAPI ejecuta las rutas síncronas en un pool)."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            self._conn.commit()
            return rows

    def close(self) -> None:
        with self._lock:
            self._conn.close()
