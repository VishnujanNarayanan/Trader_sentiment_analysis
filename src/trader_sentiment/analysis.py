"""The summary tables the whole project exists to produce."""
from __future__ import annotations

import pandas as pd

from .config import SENTIMENT_ORDER

BUY, SELL = "BUY", "SELL"


def order_sentiment(frame: pd.DataFrame, column: str = "sentiment") -> pd.DataFrame:
    """Sort rows fear-to-greed rather than alphabetically.

    Alphabetical order puts Extreme Greed second and Neutral last, which makes
    every chart read as noise instead of a gradient.
    """
    present = [s for s in SENTIMENT_ORDER if s in set(frame[column])]
    return frame.set_index(column).loc[present].reset_index()


def summary_by_sentiment(trades: pd.DataFrame) -> pd.DataFrame:
    """Average realised PnL, typical position and trade count per sentiment band.

    The position is a median: it is a long-tailed quantity where a handful of
    very large books drag a mean somewhere no actual trader sits.
    """
    out = trades.groupby("sentiment").agg(
        avg_closed_pnl=("Closed PnL", "mean"),
        median_start_position=("Start Position", "median"),
        avg_trade_size_usd=("Size USD", "mean"),
        trade_count=("Closed PnL", "size"),
    ).reset_index()
    return order_sentiment(out)


def summary_by_sentiment_and_side(trades: pd.DataFrame) -> pd.DataFrame:
    """The headline table: does the buyer or the seller earn more, per band?"""
    out = trades.groupby(["sentiment", "Side"]).agg(
        avg_closed_pnl=("Closed PnL", "mean"),
        traded_volume_usd=("Size USD", "sum"),
        trade_count=("Closed PnL", "size"),
    ).reset_index()
    return order_sentiment(out)


def pnl_matrix(trades: pd.DataFrame) -> pd.DataFrame:
    """Sentiment x side grid of average PnL -- the heatmap behind the finding."""
    grid = trades.pivot_table(
        index="sentiment", columns="Side", values="Closed PnL", aggfunc="mean"
    )
    present = [s for s in SENTIMENT_ORDER if s in grid.index]
    return grid.loc[present]


def contrarian_edge(trades: pd.DataFrame) -> pd.DataFrame:
    """Buy-minus-sell PnL per band: positive means buyers earned more.

    This is the claim stated as a number. "Be greedy when others are fearful"
    predicts a positive edge under fear and a negative one under greed.
    """
    grid = pnl_matrix(trades)
    if BUY not in grid.columns or SELL not in grid.columns:
        raise ValueError("both BUY and SELL sides are required to compute an edge")
    out = pd.DataFrame({
        "sentiment": grid.index,
        "buy_pnl": grid[BUY].to_numpy(),
        "sell_pnl": grid[SELL].to_numpy(),
    })
    out["buy_minus_sell"] = out["buy_pnl"] - out["sell_pnl"]
    out["favours"] = out["buy_minus_sell"].map(lambda d: BUY if d > 0 else SELL)
    return out
