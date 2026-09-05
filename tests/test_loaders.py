import pandas as pd

from trader_sentiment.loaders import load_trades


def test_day_first_timestamps_are_not_read_as_month_first(trades_csv):
    trades = load_trades(trades_csv)
    # "02-12-2024" is 2 December, not 12 February
    assert trades["date"].iloc[0] == pd.Timestamp("2024-12-02").date()
    assert trades["time_ist"].iloc[0] == pd.Timestamp("2024-12-02 22:50")


def test_only_the_used_columns_are_read(trades_csv):
    trades = load_trades(trades_csv)
    assert "Closed PnL" in trades.columns
    assert "Side" in trades.columns
    assert len(trades) == 5
