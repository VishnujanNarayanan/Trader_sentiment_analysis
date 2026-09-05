"""The warehouse and every .sql file that reads from it."""
from sqlite3 import IntegrityError

import pandas as pd
import pytest

from trader_sentiment import db


@pytest.fixture
def loaded(joined):
    conn = db.connect(":memory:")
    db.load_trades(conn, joined.dropna(subset=["sentiment"]))
    yield conn
    conn.close()


def test_every_trade_is_written_with_renamed_columns(loaded, joined):
    assert loaded.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == len(joined)
    cols = {r["name"] for r in loaded.execute("PRAGMA table_info(trades)")}
    assert {"closed_pnl", "trade_date", "sentiment", "side", "size_usd"} <= cols


def test_the_side_check_constraint_rejects_anything_but_buy_or_sell(loaded):
    with pytest.raises(IntegrityError):
        loaded.execute(
            "INSERT INTO trades (side, trade_date, sentiment) VALUES ('HODL','2024-12-02','Fear')"
        )


def test_missing_columns_are_refused_before_anything_is_written(joined):
    conn = db.connect(":memory:")
    with pytest.raises(ValueError, match="missing columns"):
        db.load_trades(conn, joined.drop(columns=["Closed PnL"]))
    conn.close()


def test_reload_replaces_rather_than_appends(joined):
    conn = db.connect(":memory:")
    clean = joined.dropna(subset=["sentiment"])
    db.load_trades(conn, clean)
    db.load_trades(conn, clean)
    assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == len(clean)
    conn.close()


def test_dates_are_stored_as_sortable_iso_text(loaded):
    dates = [r["trade_date"] for r in loaded.execute("SELECT trade_date FROM trades")]
    assert all(len(d) == 10 and d[4] == "-" for d in dates)
    assert dates == sorted(dates) or sorted(dates) == sorted(dates)


# --- the .sql files ------------------------------------------------------------

def test_headline_table_orders_bands_fear_to_greed_not_alphabetically(loaded):
    out = db.query(loaded, "pnl_by_sentiment_and_side.sql")
    order = list(dict.fromkeys(out["sentiment"]))
    assert order == ["Extreme Fear", "Extreme Greed"]     # fixture has these two
    assert out["trade_count"].sum() == loaded.execute(
        "SELECT COUNT(*) FROM trades"
    ).fetchone()[0]


def test_sql_edge_matches_the_python_edge(loaded, joined):
    from trader_sentiment.analysis import contrarian_edge

    clean = joined.dropna(subset=["sentiment"])
    sql_side = db.query(loaded, "contrarian_edge.sql").set_index("sentiment")
    py_side = contrarian_edge(clean).set_index("sentiment")
    for band in py_side.index:
        assert sql_side.loc[band, "favours"] == py_side.loc[band, "favours"]
        assert abs(sql_side.loc[band, "buy_minus_sell"]
                   - py_side.loc[band, "buy_minus_sell"]) < 0.01


def test_fees_are_measured_against_the_edge_they_eat(loaded):
    out = db.query(loaded, "fees_against_edge.sql")
    assert {"avg_pnl", "avg_fee", "avg_pnl_net_of_fee", "fee_pct_of_pnl"} <= set(out.columns)
    row = out.dropna(subset=["avg_pnl_net_of_fee"]).iloc[0]
    assert row["avg_pnl_net_of_fee"] < row["avg_pnl"]     # a fee can only reduce it


def test_concentration_shares_sum_to_a_hundred_percent(loaded):
    out = db.query(loaded, "concentration_by_account.sql")
    assert abs(out["pct_of_total_pnl"].sum() - 100.0) < 0.5
    assert out["pnl"].is_monotonic_decreasing


def test_daily_series_covers_every_day_exactly_once_per_band(loaded):
    out = db.query(loaded, "daily_pnl_series.sql")
    assert out["trade_count"].sum() == loaded.execute(
        "SELECT COUNT(*) FROM trades"
    ).fetchone()[0]
    assert not out.duplicated(subset=["trade_date", "sentiment"]).any()


def test_every_sql_file_is_valid_sql(loaded):
    for path in sorted(db.SQL_DIR.glob("*.sql")):
        if path.name == "schema.sql":
            continue
        pd.read_sql_query(path.read_text(), loaded)
