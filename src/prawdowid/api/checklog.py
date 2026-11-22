"""Log sprawdzeń w SQLite (FR-70, FR-71, FR-51, FR-81, FR-82).

Jeden wiersz na sprawdzenie: kiedy, którym kanałem, pytanie (z zamaskowanymi danymi osobowymi),
wynik, użyte źródła, model, czas odpowiedzi, koszt, błędy pobierania stron, wstrzymanie się
i próba prompt injection.

Minimalizacja danych:
- strona WWW nie identyfikuje użytkownika (brak user_ref, IP, ciasteczek),
- Discord przekazuje tylko pseudonim (HMAC z solą), nigdy ID Discorda,
- treść pytania zapisujemy wyłącznie po maskowaniu (pii.mask),
- wpisy starsze niż LOG_RETENTION_DAYS są usuwane automatycznie (purge),
- pojedyncze sprawdzenie można usunąć od razu (delete) - po usunięciu nie ma po nim śladu w bazie.
"""

import json
import sqlite3
import statistics
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from prawdowid.api.settings import CHECK_LOG_DB, LOG_RETENTION_DAYS

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    check_id        TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,      -- UTC, ISO 8601
    channel         TEXT NOT NULL,      -- WEB | DISCORD | ...
    user_ref        TEXT,               -- pseudonim (Discord), NULL dla strony WWW
    conversation_id TEXT,
    question        TEXT,               -- po maskowaniu danych osobowych
    url             TEXT,
    pii_masked      TEXT,               -- rodzaje zamaskowanych danych, np. "EMAIL,TELEFON"
    status          TEXT NOT NULL,      -- COMPLETED | NEEDS_CLARIFICATION | OUT_OF_SCOPE | TECHNICAL_FAILURE | TEXT
    verdicts        TEXT,               -- JSON: lista werdyktów twierdzeń
    sources         TEXT,               -- JSON: adresy źródeł pokazanych jako dowody
    abstained       INTEGER NOT NULL DEFAULT 0,  -- wstrzymanie się (brak wystarczających dowodów)
    injection       INTEGER NOT NULL DEFAULT 0,  -- wykryta próba prompt injection
    rejection       TEXT,               -- kategoria odrzucenia ze skilla walidacji
    error           TEXT,               -- komunikat błędu technicznego
    model           TEXT,               -- dostawca/model
    latency_ms      INTEGER,
    cost_usd        REAL,               -- koszt zgłoszony przez OpenCode
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    fetches         INTEGER,            -- liczba pobrań stron przez agenta
    fetch_errors    INTEGER             -- pobrania nieudane lub zablokowane
);
CREATE INDEX IF NOT EXISTS checks_created ON checks(created_at);
CREATE INDEX IF NOT EXISTS checks_conversation ON checks(conversation_id);
"""

COLUMNS = ("check_id", "created_at", "channel", "user_ref", "conversation_id", "question", "url", "pii_masked",
           "status", "verdicts", "sources", "abstained", "injection", "rejection", "error", "model", "latency_ms",
           "cost_usd", "tokens_in", "tokens_out", "fetches", "fetch_errors")
JSON_COLUMNS = ("verdicts", "sources")


def _connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def init(db: Path = CHECK_LOG_DB) -> None:
    with closing(_connect(db)) as conn, conn:
        conn.executescript(SCHEMA)


def record(entry: dict, db: Path = CHECK_LOG_DB) -> None:
    row = {c: entry.get(c) for c in COLUMNS}
    row["created_at"] = row["created_at"] or datetime.now(UTC).isoformat(timespec="seconds")
    for c in JSON_COLUMNS:
        if row[c] is not None:
            row[c] = json.dumps(row[c], ensure_ascii=False)
    row["abstained"] = int(bool(row["abstained"]))
    row["injection"] = int(bool(row["injection"]))
    with closing(_connect(db)) as conn, conn:
        conn.execute(f"INSERT OR REPLACE INTO checks ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                     [row[c] for c in COLUMNS])


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for c in JSON_COLUMNS:
        d[c] = json.loads(d[c]) if d[c] else []
    d["abstained"], d["injection"] = bool(d["abstained"]), bool(d["injection"])
    return d


def get(check_id: str, db: Path = CHECK_LOG_DB) -> dict | None:
    with closing(_connect(db)) as conn:
        r = conn.execute("SELECT * FROM checks WHERE check_id = ?", (check_id,)).fetchone()
    return _row(r) if r else None


def recent(limit: int = 50, db: Path = CHECK_LOG_DB) -> list[dict]:
    with closing(_connect(db)) as conn:
        rows = conn.execute("SELECT * FROM checks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def delete(check_id: str, db: Path = CHECK_LOG_DB) -> bool:
    """Usuwa jedno sprawdzenie (FR-82). True, gdy było co usunąć."""
    with closing(_connect(db)) as conn, conn:
        return conn.execute("DELETE FROM checks WHERE check_id = ?", (check_id,)).rowcount > 0


def purge(days: float = LOG_RETENTION_DAYS, db: Path = CHECK_LOG_DB) -> int:
    """Usuwa wpisy starsze niż okres retencji (FR-81). Zwraca liczbę usuniętych wpisów."""
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")
    with closing(_connect(db)) as conn, conn:
        return conn.execute("DELETE FROM checks WHERE created_at < ?", (cutoff,)).rowcount


def summary(db: Path = CHECK_LOG_DB) -> dict:
    """Zbiorcze liczby dla jury: ile sprawdzeń, mediana czasu, koszt, wstrzymania, odrzucone ataki."""
    with closing(_connect(db)) as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT status, latency_ms, cost_usd, abstained, injection, fetch_errors, channel FROM checks")]
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None and r["status"] != "TECHNICAL_FAILURE"]
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    by = lambda key: {v: sum(1 for r in rows if r[key] == v) for v in sorted({r[key] for r in rows})}  # noqa: E731
    return {
        "checks": len(rows),
        "byStatus": by("status"),
        "byChannel": by("channel"),
        "medianLatencyMs": int(statistics.median(latencies)) if latencies else None,
        "totalCostUsd": round(sum(costs), 6) if costs else None,
        "avgCostUsd": round(sum(costs) / len(costs), 6) if costs else None,
        "abstained": sum(r["abstained"] for r in rows),
        "injectionAttempts": sum(r["injection"] for r in rows),
        "fetchErrors": sum(r["fetch_errors"] or 0 for r in rows),
        "retentionDays": LOG_RETENTION_DAYS,
    }
