"""Can market sentiment predict whether a trade closes profitable?

The analysis showed a difference in AVERAGE PnL between sentiment bands. That is
not the same claim as being able to call an INDIVIDUAL trade, and conflating the
two is how a backtest starts lying. This module tests the second, harder claim
directly with a classifier, and reports it against the base rate so a small
improvement cannot masquerade as a large one.

Every feature here is knowable at the moment the trade is placed. Closed PnL and
anything derived from it is the label, never an input.

A leak found the hard way, recorded so it is not reintroduced: labelling every
row ``closed_pnl > 0`` scored ROC-AUC 0.94, which is not a plausible number for
predicting trade profitability. It was not signal. 51.9% of the export's rows
are opens and adds, which carry ``closed_pnl == 0`` and were all being labelled
"not profitable" -- so the model was mostly learning to recognise which rows
were closes, a question about the file format rather than about the market.
``Start Position == 0`` separated them perfectly and took 55% of the feature
importance. Restricted to genuine closes, the honest score is ROC-AUC 0.53.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .config import SENTIMENT_ORDER

#: Inputs known before the outcome is. Deliberately short: this is a test of
#: whether sentiment carries signal, not a race to the best possible score.
NUMERIC_FEATURES = ["size_usd", "execution_price", "start_position", "log_size_usd"]

#: Never an input, at any point. Named so the leakage test can assert on it.
FORBIDDEN_FEATURES = ["closed_pnl", "Closed PnL", "profitable", "fee", "Fee"]


def closing_trades(trades: pd.DataFrame, pnl_column: str = "Closed PnL") -> pd.DataFrame:
    """Keep only rows that actually closed a position.

    An open or an add carries ``closed_pnl == 0``: no position was closed, so
    there is no outcome to predict. Including them makes the label mean "is this
    a close?" rather than "did this close make money", which is a question about
    the export format and is trivially answerable from Start Position.
    """
    return trades[trades[pnl_column] != 0].reset_index(drop=True)


def build_features(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Trades -> (X, y), where y is 1 when the trade closed profitable.

    Size is log-scaled with NumPy because position sizes span several orders of
    magnitude; untransformed, a handful of very large trades dominate every
    split the tree makes.
    """
    frame = trades.rename(columns={
        "Size USD": "size_usd", "Execution Price": "execution_price",
        "Start Position": "start_position", "Closed PnL": "closed_pnl", "Side": "side",
    })
    y = (frame["closed_pnl"] > 0).astype(int).rename("profitable")

    features = pd.DataFrame(index=frame.index)
    features["size_usd"] = frame["size_usd"].astype(float)
    features["execution_price"] = frame["execution_price"].astype(float)
    features["start_position"] = frame["start_position"].astype(float)
    features["log_size_usd"] = np.log1p(np.abs(features["size_usd"].to_numpy()))
    features["is_buy"] = (frame["side"].str.upper() == "BUY").astype(int)

    for band in SENTIMENT_ORDER:
        features[f"sentiment_{band.replace(' ', '_').lower()}"] = (
            frame["sentiment"] == band
        ).astype(int)

    return features.fillna(0.0), y


def time_ordered_split(trades: pd.DataFrame, train_frac: float = 0.7,
                       date_column: str = "date"):
    """Split on the calendar, not at random.

    A random split lets the model learn from days that come after the ones it is
    scored on. The sentiment index moves slowly and in regimes, so a random
    split is close to telling the model the answer.
    """
    if not 0 < train_frac < 1:
        raise ValueError("train_frac must sit strictly between 0 and 1")
    dates = np.sort(pd.to_datetime(trades[date_column]).unique())
    cutoff = dates[int(len(dates) * train_frac)]
    stamps = pd.to_datetime(trades[date_column])
    return trades[stamps < cutoff].copy(), trades[stamps >= cutoff].copy()


def train(x_train: pd.DataFrame, y_train: pd.Series, **kwargs) -> RandomForestClassifier:
    """Fit the classifier. Seeded, so two runs of the report agree."""
    params = {"n_estimators": 200, "min_samples_leaf": 50, "random_state": 42,
              "n_jobs": -1, "class_weight": "balanced"}
    params.update(kwargs)
    model = RandomForestClassifier(**params)
    model.fit(x_train, y_train)
    return model


def evaluate(model: RandomForestClassifier, x_test: pd.DataFrame,
             y_test: pd.Series, threshold: float = 0.5) -> dict:
    """Score the model, and report the base rate beside every number.

    'Accuracy 0.58' means nothing on its own. If 58% of trades close profitable,
    predicting 'profitable' every time scores the same, and the model has
    learned nothing at all -- so the lift over that baseline is the only figure
    here worth reading.
    """
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)
    base_rate = float(y_test.mean())
    accuracy = float(accuracy_score(y_test, predictions))
    return {
        "base_rate": base_rate,
        "accuracy": accuracy,
        "accuracy_lift_over_base": accuracy - max(base_rate, 1 - base_rate),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "n_test": int(len(y_test)),
        "report": classification_report(y_test, predictions, zero_division=0),
    }


def feature_importance(model: RandomForestClassifier, columns) -> pd.DataFrame:
    """Which inputs the forest actually leaned on."""
    return pd.DataFrame({
        "feature": list(columns),
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)
