"""The classifier, and the traps that make a model look better than it is."""
import numpy as np
import pandas as pd
import pytest

from trader_sentiment.model import (
    FORBIDDEN_FEATURES,
    build_features,
    evaluate,
    feature_importance,
    time_ordered_split,
    train,
)


@pytest.fixture
def learnable():
    """A dataset where sentiment genuinely predicts the outcome.

    Buys under fear and sells under greed win most of the time; everything else
    is a coin flip. A model that cannot find this is broken.
    """
    rng = np.random.default_rng(0)
    rows = []
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    for i, day in enumerate(dates):
        band = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"][i % 5]
        for _ in range(60):
            side = rng.choice(["BUY", "SELL"])
            favoured = (side == "BUY" and "Fear" in band) or (side == "SELL" and "Greed" in band)
            wins = rng.random() < (0.85 if favoured else 0.5)
            rows.append({
                "date": day.date(), "sentiment": band, "Side": side,
                "Size USD": float(rng.lognormal(6, 1)),
                "Execution Price": float(rng.uniform(10, 100)),
                "Start Position": float(rng.normal(0, 100)),
                "Closed PnL": float(abs(rng.normal(20, 5))) * (1 if wins else -1),
            })
    return pd.DataFrame(rows)


def test_the_label_and_its_ingredients_are_never_features(learnable):
    x, _ = build_features(learnable)
    for banned in FORBIDDEN_FEATURES:
        assert banned not in x.columns
    assert not any("pnl" in c.lower() for c in x.columns)


def test_the_label_is_profitability_not_the_amount(learnable):
    _, y = build_features(learnable)
    assert set(y.unique()) <= {0, 1}
    assert y.sum() == (learnable["Closed PnL"] > 0).sum()


def test_every_sentiment_band_gets_its_own_column(learnable):
    x, _ = build_features(learnable)
    bands = [c for c in x.columns if c.startswith("sentiment_")]
    assert len(bands) == 5
    assert x[bands].sum(axis=1).eq(1).all()      # exactly one band per trade


def test_size_is_log_scaled_so_a_few_whales_do_not_dominate(learnable):
    x, _ = build_features(learnable)
    assert x["log_size_usd"].std() < x["size_usd"].std()
    assert np.allclose(x["log_size_usd"], np.log1p(np.abs(x["size_usd"])))


def test_the_split_is_chronological_with_no_overlap(learnable):
    train_df, test_df = time_ordered_split(learnable, train_frac=0.7)
    assert max(train_df["date"]) < min(test_df["date"])
    assert len(train_df) + len(test_df) == len(learnable)


def test_an_impossible_split_fraction_is_rejected(learnable):
    for bad in (0.0, 1.0, -0.5, 2.0):
        with pytest.raises(ValueError):
            time_ordered_split(learnable, train_frac=bad)


def test_the_model_finds_a_signal_that_is_really_there(learnable):
    train_df, test_df = time_ordered_split(learnable)
    x_tr, y_tr = build_features(train_df)
    x_te, y_te = build_features(test_df)
    scores = evaluate(train(x_tr, y_tr), x_te, y_te)
    assert scores["roc_auc"] > 0.6
    assert scores["accuracy_lift_over_base"] > 0


def test_the_model_finds_nothing_when_there_is_nothing(learnable):
    """The important direction: noise must not produce a confident model."""
    noise = learnable.copy()
    rng = np.random.default_rng(1)
    noise["Closed PnL"] = rng.normal(0, 20, len(noise))
    train_df, test_df = time_ordered_split(noise)
    x_tr, y_tr = build_features(train_df)
    x_te, y_te = build_features(test_df)
    scores = evaluate(train(x_tr, y_tr), x_te, y_te)
    assert scores["roc_auc"] < 0.6


def test_evaluation_reports_the_base_rate_beside_the_accuracy(learnable):
    train_df, test_df = time_ordered_split(learnable)
    x_tr, y_tr = build_features(train_df)
    x_te, y_te = build_features(test_df)
    scores = evaluate(train(x_tr, y_tr), x_te, y_te)
    assert 0 <= scores["base_rate"] <= 1
    assert scores["n_test"] == len(y_te)
    # the lift is the accuracy minus what always guessing the majority would get
    assert scores["accuracy_lift_over_base"] == pytest.approx(
        scores["accuracy"] - max(scores["base_rate"], 1 - scores["base_rate"])
    )


def test_training_is_seeded_so_the_report_is_reproducible(learnable):
    x, y = build_features(learnable)
    a = train(x, y).predict_proba(x)[:, 1]
    b = train(x, y).predict_proba(x)[:, 1]
    assert np.allclose(a, b)


def test_importances_name_real_columns_and_sum_to_one(learnable):
    x, y = build_features(learnable)
    imp = feature_importance(train(x, y), x.columns)
    assert set(imp["feature"]) == set(x.columns)
    assert imp["importance"].sum() == pytest.approx(1.0)
    assert imp["importance"].is_monotonic_decreasing


# --- the leakage that scored 0.94 ------------------------------------------------

def test_opens_and_adds_are_excluded_because_they_have_no_outcome():
    """The bug that produced a fake ROC-AUC of 0.94.

    An open carries closed_pnl == 0. Labelling it "not profitable" turns the
    task into "is this row a close?", which Start Position answers outright.
    """
    from trader_sentiment.model import closing_trades

    frame = pd.DataFrame({
        "Closed PnL": [10.0, 0.0, -5.0, 0.0],
        "Start Position": [100.0, 0.0, 50.0, 0.0],
    })
    out = closing_trades(frame)
    assert len(out) == 2
    assert (out["Closed PnL"] != 0).all()


def test_start_position_no_longer_separates_the_label_once_opens_are_gone():
    """On the real export, Start Position == 0 implied closed_pnl == 0 exactly.

    After filtering to closes that implication has to be gone, or the leak is
    still there under a different name.
    """
    from trader_sentiment.model import closing_trades

    frame = pd.DataFrame({
        "Closed PnL": [10.0, 0.0, -5.0, 0.0, 3.0],
        "Start Position": [100.0, 0.0, 0.0, 0.0, 50.0],
    })
    out = closing_trades(frame)
    zero_position = out[out["Start Position"] == 0]
    assert len(zero_position) == 1
    assert (zero_position["Closed PnL"] != 0).all()


def test_a_model_on_pure_noise_does_not_beat_the_coin_flip(learnable):
    """Guards the direction that matters: no signal must score like no signal."""
    from trader_sentiment.model import build_features, evaluate, time_ordered_split, train

    rng = np.random.default_rng(11)
    noise = learnable.copy()
    noise["sentiment"] = rng.choice(["Fear", "Greed", "Neutral"], len(noise))
    noise["Closed PnL"] = rng.normal(0, 20, len(noise))
    tr_df, te_df = time_ordered_split(noise)
    x_tr, y_tr = build_features(tr_df)
    x_te, y_te = build_features(te_df)
    assert evaluate(train(x_tr, y_tr), x_te, y_te)["roc_auc"] < 0.6
