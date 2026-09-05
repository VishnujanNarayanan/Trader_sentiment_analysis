-- One row per trade, already carrying the sentiment band of the day it was
-- placed. The join and the cleaning happen once, on the way in; every question
-- below is then a query rather than a re-run of the whole pipeline.

DROP TABLE IF EXISTS trades;

CREATE TABLE trades (
    account         TEXT,
    coin            TEXT,
    side            TEXT    NOT NULL CHECK (side IN ('BUY', 'SELL')),
    trade_date      TEXT    NOT NULL,   -- ISO-8601 date
    size_usd        REAL,
    execution_price REAL,
    start_position  REAL,
    closed_pnl      REAL,
    fee             REAL,
    sentiment       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_sentiment ON trades (sentiment);
CREATE INDEX IF NOT EXISTS idx_trades_date      ON trades (trade_date);
CREATE INDEX IF NOT EXISTS idx_trades_side      ON trades (side);
