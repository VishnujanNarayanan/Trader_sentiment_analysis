"""Join trades to sentiment, and handle the two things that skew the result.

Both fixes were in the notebook already; they are here so they can be tested and
so the reasons survive next to the code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def join_sentiment(trades: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    """Attach each trade the sentiment classification of the day it was placed.

    A left join on purpose: an unmatched trade must stay visible so
    ``missing_sentiment_report`` can count it, rather than vanishing silently.
    """
    index = sentiment[["date", "classification"]].rename(columns={"classification": "sentiment"})
    return trades.merge(index, on="date", how="left")


def missing_sentiment_report(joined: pd.DataFrame) -> dict:
    """How many trades fell outside the index's coverage, and what share that is."""
    missing = int(joined["sentiment"].isna().sum())
    total = int(len(joined))
    return {
        "missing": missing,
        "total": total,
        "pct": round(100 * missing / total, 4) if total else 0.0,
    }


def drop_unmatched(joined: pd.DataFrame) -> pd.DataFrame:
    return joined.dropna(subset=["sentiment"]).reset_index(drop=True)


def iqr_bounds(series: pd.Series, k: float = 3.0) -> tuple[float, float]:
    """Tukey fences at ``k`` times the interquartile range.

    k=3 rather than the usual 1.5: the intent is to drop positions that are
    implausible, not to trim the tails of a genuinely heavy-tailed distribution.
    """
    q1, q3 = np.percentile(series.dropna(), [25, 75])
    spread = q3 - q1
    return float(q1 - k * spread), float(q3 + k * spread)


def filter_outliers(frame: pd.DataFrame, column: str = "Start Position", k: float = 3.0):
    """Drop rows whose ``column`` sits outside the IQR fences."""
    low, high = iqr_bounds(frame[column], k=k)
    keep = frame[column].between(low, high)
    return frame[keep].reset_index(drop=True)


def prepare(trades: pd.DataFrame, sentiment: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The whole cleaning path: join, report coverage, drop unmatched, defence."""
    joined = join_sentiment(trades, sentiment)
    report = missing_sentiment_report(joined)
    cleaned = filter_outliers(drop_unmatched(joined))
    return cleaned, report
