import numpy as np
import pandas as pd
import pytest

from trader_sentiment.analysis import (
    contrarian_edge,
    order_sentiment,
    pnl_matrix,
    summary_by_sentiment,
    summary_by_sentiment_and_side,
)


@pytest.fixture
def graded():
    """A frame where the contrarian story is true by construction.

    Under fear buyers earn more; under greed sellers do. If the code cannot
    recover a pattern this blatant it will not recover a real one.
    """
    rows = []
    for sentiment, buy_pnl, sell_pnl in [
        ("Extreme Fear", 60.0, 10.0),
        ("Fear", 50.0, 20.0),
        ("Neutral", 30.0, 30.0),
        ("Greed", 20.0, 40.0),
        ("Extreme Greed", 5.0, 70.0),
    ]:
        for side, pnl in (("BUY", buy_pnl), ("SELL", sell_pnl)):
            for i in range(4):
                rows.append({
                    "sentiment": sentiment, "Side": side,
                    "Closed PnL": pnl + i, "Size USD": 100.0,
                    "Start Position": 10.0 * (i + 1),
                })
    return pd.DataFrame(rows)


def test_bands_are_ordered_fear_to_greed_not_alphabetically(graded):
    out = order_sentiment(graded[["sentiment", "Closed PnL"]].drop_duplicates("sentiment"))
    assert out["sentiment"].tolist() == [
        "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    ]
    # alphabetical would have put Extreme Greed second and Neutral last
    assert out["sentiment"].tolist() != sorted(out["sentiment"].tolist())


def test_ordering_survives_a_band_being_absent(graded):
    out = order_sentiment(graded[graded.sentiment != "Neutral"])
    assert "Neutral" not in set(out["sentiment"])
    assert out["sentiment"].iloc[0] == "Extreme Fear"


def test_position_is_summarised_by_median_not_mean(graded):
    skewed = graded.copy()
    skewed.loc[skewed.index[0], "Start Position"] = 10**9
    out = summary_by_sentiment(skewed).set_index("sentiment")
    assert out.loc["Extreme Fear", "median_start_position"] < 100


def test_side_summary_reports_both_sides_of_every_band(graded):
    out = summary_by_sentiment_and_side(graded)
    assert len(out) == 10
    assert set(out["Side"]) == {"BUY", "SELL"}
    assert out["trade_count"].eq(4).all()


def test_the_matrix_recovers_the_planted_pattern(graded):
    grid = pnl_matrix(graded)
    assert grid.loc["Extreme Fear", "BUY"] > grid.loc["Extreme Fear", "SELL"]
    assert grid.loc["Extreme Greed", "SELL"] > grid.loc["Extreme Greed", "BUY"]


def test_edge_is_positive_under_fear_and_negative_under_greed(graded):
    edge = contrarian_edge(graded).set_index("sentiment")
    assert edge.loc["Extreme Fear", "buy_minus_sell"] > 0
    assert edge.loc["Extreme Greed", "buy_minus_sell"] < 0
    assert edge.loc["Extreme Fear", "favours"] == "BUY"
    assert edge.loc["Extreme Greed", "favours"] == "SELL"
    assert np.isclose(edge.loc["Neutral", "buy_minus_sell"], 0.0)


def test_an_edge_needs_both_sides_to_exist(graded):
    with pytest.raises(ValueError, match="both BUY and SELL"):
        contrarian_edge(graded[graded.Side == "BUY"])
