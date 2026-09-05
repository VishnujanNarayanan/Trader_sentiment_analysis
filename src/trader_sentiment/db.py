"""SQLite warehouse for the joined, cleaned trades."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import ROOT, database_path

SQL_DIR = ROOT / "sql"

#: export column -> warehouse column. The export's spaced, capitalised headers
#: are awkward to quote in every query, so they are renamed once here.
COLUMN_MAP = {
    "Account": "account",
    "Coin": "coin",
    "Side": "side",
    "date": "trade_date",
    "Size USD": "size_usd",
    "Execution Price": "execution_price",
    "Start Position": "start_position",
    "Closed PnL": "closed_pnl",
    "Fee": "fee",
    "sentiment": "sentiment",
}


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = str(path if path is not None else database_path())
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def read_sql_file(name: str) -> str:
    path = SQL_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"no such query: {path}")
    return path.read_text(encoding="utf-8")


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(read_sql_file("schema.sql"))
    conn.commit()


def load_trades(conn: sqlite3.Connection, trades: pd.DataFrame) -> int:
    """Replace the ``trades`` table with a cleaned, sentiment-joined frame."""
    missing = [c for c in COLUMN_MAP if c not in trades.columns]
    if missing:
        raise ValueError(f"trades is missing columns: {missing}")
    frame = trades[list(COLUMN_MAP)].rename(columns=COLUMN_MAP).copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.strftime("%Y-%m-%d")
    frame["side"] = frame["side"].str.upper()
    create_schema(conn)
    frame.to_sql("trades", conn, if_exists="append", index=False)
    conn.commit()
    return len(frame)


def query(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    return pd.read_sql_query(read_sql_file(name), conn)
