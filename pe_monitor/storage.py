"""SQLite-backed storage for P/E history. One table keyed by (ticker, date)."""

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    ticker             TEXT NOT NULL,
    date               TEXT NOT NULL,
    name               TEXT,
    currency           TEXT,
    price              REAL,
    trailing_eps       REAL,
    forward_eps        REAL,
    ttm_pe             REAL,
    forward_pe         REAL,
    analyst_count      INTEGER,
    financial_currency TEXT,
    forward_eps_native REAL,
    PRIMARY KEY (ticker, date)
);
"""

ROW_COLS = (
    "date", "name", "currency", "price",
    "trailing_eps", "forward_eps", "ttm_pe", "forward_pe",
    "analyst_count", "financial_currency", "forward_eps_native",
)

_MIGRATIONS = (
    ("analyst_count",      "ALTER TABLE history ADD COLUMN analyst_count INTEGER"),
    ("financial_currency", "ALTER TABLE history ADD COLUMN financial_currency TEXT"),
    ("forward_eps_native", "ALTER TABLE history ADD COLUMN forward_eps_native REAL"),
)


def init_db(db_path: str) -> None:
    """Create the database file and schema if they don't exist. Idempotent.
    Also runs additive migrations for columns added after initial release."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        existing = {r[1] for r in conn.execute("PRAGMA table_info(history)")}
        for col, ddl in _MIGRATIONS:
            if col not in existing:
                conn.execute(ddl)


def read_history(db_path: str, ticker: str) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT {', '.join(ROW_COLS)} FROM history "
            "WHERE ticker = ? ORDER BY date",
            (ticker.upper(),),
        ).fetchall()
    return [dict(r) for r in rows]


def latest_per_ticker(db_path: str, tickers: list[str]) -> list[dict]:
    """Return the most-recent row per requested ticker, with empty stubs for
    tickers that have no rows yet. Order matches the input `tickers` list."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"""
            SELECT ticker, {', '.join(ROW_COLS)} FROM history
            WHERE (ticker, date) IN (
                SELECT ticker, MAX(date) FROM history GROUP BY ticker
            )
        """).fetchall()
    by_ticker = {r["ticker"]: dict(r) for r in rows}
    result = []
    for t in tickers:
        if t in by_ticker:
            result.append(by_ticker[t])
        else:
            result.append({
                "ticker": t, "date": None, "name": "", "currency": None,
                "price": None, "trailing_eps": None, "forward_eps": None,
                "ttm_pe": None, "forward_pe": None, "analyst_count": None,
                "financial_currency": None, "forward_eps_native": None,
            })
    return result


def append_snapshot(db_path: str, ticker: str, snapshot: dict) -> None:
    """UPSERT: same-day entries are replaced (latest write wins)."""
    placeholders = ", ".join(["?"] * (1 + len(ROW_COLS)))
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in ROW_COLS if c != "date")
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"""
            INSERT INTO history (ticker, {', '.join(ROW_COLS)})
            VALUES ({placeholders})
            ON CONFLICT(ticker, date) DO UPDATE SET {update_clause}
        """, (ticker.upper(), snapshot["date"]) + tuple(
            snapshot.get(c) for c in ROW_COLS if c != "date"
        ))


def merge_history(db_path: str, ticker: str, new_rows: list[dict]) -> int:
    """Additive merge: existing (ticker, date) rows are kept untouched.

    Backfill should fill gaps, never overwrite live snapshots (which carry
    forward_pe values that backfill can't reproduce).
    Returns the number of rows actually inserted.
    """
    if not new_rows:
        return 0
    ticker = ticker.upper()
    with sqlite3.connect(db_path) as conn:
        existing = {r[0] for r in conn.execute(
            "SELECT date FROM history WHERE ticker = ?", (ticker,)
        )}
        additions = [r for r in new_rows if r["date"] not in existing]
        if not additions:
            return 0
        placeholders = ", ".join(["?"] * (1 + len(ROW_COLS)))
        conn.executemany(f"""
            INSERT INTO history (ticker, {', '.join(ROW_COLS)})
            VALUES ({placeholders})
        """, [
            (ticker,) + tuple(r.get(c) for c in ROW_COLS) for r in additions
        ])
    return len(additions)
