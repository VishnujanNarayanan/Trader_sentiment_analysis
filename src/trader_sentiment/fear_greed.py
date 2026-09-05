"""The Bitcoin Fear & Greed index, from its public API.

The README used to tell you to download a CSV from Google Drive, which the
Limitations section itself flagged: reproducibility depended on someone's Drive
link staying alive. alternative.me publishes the whole history for free, so the
project can fetch its own inputs.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd

API_URL = "https://api.alternative.me/fng/"

#: The bands alternative.me itself uses, reproduced so a value can be classified
#: offline (and so a test can assert the boundaries rather than trust the feed).
BANDS = [(24, "Extreme Fear"), (44, "Fear"), (54, "Neutral"), (74, "Greed")]


def classify(value: int) -> str:
    """Map an index value in 0-100 onto its sentiment band."""
    if not 0 <= value <= 100:
        raise ValueError(f"index value out of range: {value}")
    for ceiling, name in BANDS:
        if value <= ceiling:
            return name
    return "Extreme Greed"


def _fetch(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:   # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def to_frame(payload: dict) -> pd.DataFrame:
    """API payload -> the four columns the analysis expects.

    Kept separate from the network call so the parsing is testable without one.
    """
    rows = payload.get("data")
    if not rows:
        raise ValueError("Fear & Greed payload contained no data")
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_numeric(frame["timestamp"])
    frame["value"] = pd.to_numeric(frame["value"])
    frame["classification"] = frame["value_classification"]
    frame["date"] = pd.to_datetime(frame["timestamp"], unit="s").dt.date
    return frame[["timestamp", "value", "classification", "date"]].sort_values("date")


def fetch(limit: int = 0, timeout: float = 30.0) -> pd.DataFrame:
    """Download the index. ``limit=0`` means the entire published history."""
    return to_frame(_fetch(f"{API_URL}?limit={limit}&format=json", timeout))


def load_or_fetch(path: str | Path, limit: int = 0) -> pd.DataFrame:
    """Read the local snapshot, downloading and caching it the first time."""
    path = Path(path)
    if path.exists():
        frame = pd.read_csv(path)
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        return frame
    frame = fetch(limit=limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame
