"""Where the data lives.

The notebook read from two hardcoded Windows desktop paths, and the README
pointed at two Google Drive links -- so the analysis was reproducible only on
one machine, and only for as long as those links stayed alive. Paths now resolve
from the environment, and the sentiment index is fetched from its public API.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Sentiment bands, in the order they should appear on every axis and table.
SENTIMENT_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]


def data_dir() -> Path:
    return Path(os.environ.get("TS_DATA_DIR", ROOT / "data"))


def trades_csv() -> Path:
    """Hyperliquid trade history. Override with TS_TRADES_CSV."""
    return Path(os.environ.get("TS_TRADES_CSV", data_dir() / "historical_data.csv"))


def fear_greed_csv() -> Path:
    """Local snapshot of the Fear & Greed index. Override with TS_FEAR_GREED_CSV."""
    return Path(os.environ.get("TS_FEAR_GREED_CSV", data_dir() / "fear_greed_index.csv"))


def database_path() -> Path:
    return Path(os.environ.get("TS_DB_PATH", data_dir() / "trader_sentiment.db"))
