"""Fixtures shaped like the real exports, small enough to reason about by hand."""
import pandas as pd
import pytest


@pytest.fixture
def trades_csv(tmp_path):
    """A Hyperliquid-shaped export: two dates, both sides, one extreme position."""
    rows = [
        # Account, Coin, ExecPrice, SizeTokens, SizeUSD, Side,
        # Timestamp IST, StartPos, Direction, PnL, Fee
        ("0xa", "BTC", 100.0, 1.0, 100.0, "BUY", "02-12-2024 22:50", 0, "Buy", 10.0, 0.1),
        ("0xa", "BTC", 101.0, 1.0, 101.0, "SELL", "02-12-2024 23:50", 10, "Sell", -5.0, 0.1),
        ("0xb", "ETH", 50.0, 2.0, 100.0, "BUY", "03-12-2024 10:00", 5, "Buy", 20.0, 0.2),
        ("0xb", "ETH", 51.0, 2.0, 102.0, "SELL", "03-12-2024 11:00", 5, "Sell", 30.0, 0.2),
        ("0xc", "SOL", 10.0, 10.0, 100.0, "BUY", "03-12-2024 12:00", 10**9, "Buy", 1.0, 0.1),
    ]
    frame = pd.DataFrame(rows, columns=[
        "Account", "Coin", "Execution Price", "Size Tokens", "Size USD", "Side",
        "Timestamp IST", "Start Position", "Direction", "Closed PnL", "Fee",
    ])
    path = tmp_path / "historical_data.csv"
    frame.to_csv(path, index=False)
    return path


@pytest.fixture
def fear_greed_frame():
    return pd.DataFrame({
        "timestamp": [1733097600, 1733184000],
        "value": [20, 80],
        "classification": ["Extreme Fear", "Extreme Greed"],
        "date": [pd.Timestamp("2024-12-02").date(), pd.Timestamp("2024-12-03").date()],
    })


@pytest.fixture
def joined(trades_csv, fear_greed_frame):
    from trader_sentiment.clean import join_sentiment
    from trader_sentiment.loaders import load_trades

    return join_sentiment(load_trades(trades_csv), fear_greed_frame)
