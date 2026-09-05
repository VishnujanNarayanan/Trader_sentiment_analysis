import pandas as pd

from trader_sentiment.clean import (
    drop_unmatched,
    filter_outliers,
    iqr_bounds,
    join_sentiment,
    missing_sentiment_report,
    prepare,
)


def test_a_trade_inherits_the_sentiment_of_its_own_day(joined):
    dec2 = joined[joined.date == pd.Timestamp("2024-12-02").date()]
    dec3 = joined[joined.date == pd.Timestamp("2024-12-03").date()]
    assert set(dec2["sentiment"]) == {"Extreme Fear"}
    assert set(dec3["sentiment"]) == {"Extreme Greed"}


def test_unmatched_trades_survive_the_join_so_they_can_be_counted(trades_csv, fear_greed_frame):
    from trader_sentiment.loaders import load_trades

    partial = fear_greed_frame.iloc[:1]           # only 2 December is covered
    out = join_sentiment(load_trades(trades_csv), partial)
    assert len(out) == 5                          # nothing dropped by the join itself
    report = missing_sentiment_report(out)
    assert report["missing"] == 3
    assert report["total"] == 5
    assert report["pct"] == 60.0
    assert len(drop_unmatched(out)) == 2


def test_iqr_fences_use_three_times_the_spread():
    series = pd.Series([1, 2, 3, 4])              # q1=1.75, q3=3.25, iqr=1.5
    low, high = iqr_bounds(series, k=3.0)
    assert low == 1.75 - 4.5
    assert high == 3.25 + 4.5


def test_an_implausible_position_is_dropped_and_normal_ones_are_kept(joined):
    assert (joined["Start Position"] > 10**8).any()
    cleaned = filter_outliers(joined)
    assert (cleaned["Start Position"] > 10**8).sum() == 0
    assert len(cleaned) == 4


def test_prepare_reports_coverage_before_it_drops_anything(trades_csv, fear_greed_frame):
    from trader_sentiment.loaders import load_trades

    cleaned, report = prepare(load_trades(trades_csv), fear_greed_frame)
    assert report["total"] == 5                   # counted pre-drop
    assert report["missing"] == 0
    assert len(cleaned) == 4                      # the outlier is gone
