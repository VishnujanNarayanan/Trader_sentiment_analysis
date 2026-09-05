"""Build the warehouse end to end.

    python -m trader_sentiment.build --db data/trader_sentiment.db
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import clean, config, db, fear_greed, loaders

log = logging.getLogger("trader_sentiment.build")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trades", type=Path, default=None)
    parser.add_argument("--fear-greed", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    trades = loaders.load_trades(args.trades or config.trades_csv())
    log.info("loaded %d trades", len(trades))
    sentiment = fear_greed.load_or_fetch(args.fear_greed or config.fear_greed_csv())
    log.info("loaded %d daily sentiment readings", len(sentiment))

    cleaned, report = clean.prepare(trades, sentiment)
    log.info("%d of %d trades had no sentiment for their day (%.4f%%)",
             report["missing"], report["total"], report["pct"])
    log.info("%d trades remain after the position filter", len(cleaned))

    conn = db.connect(args.db)
    try:
        written = db.load_trades(conn, cleaned)
    finally:
        conn.close()
    log.info("wrote %d rows to %s", written, args.db or config.database_path())
    return 0


if __name__ == "__main__":
    sys.exit(main())
