"""Read the Hyperliquid trade history."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Columns the analysis actually uses. The export carries more (hashes, order
#: ids, fees); reading only these keeps a 47MB file cheap to load.
USED_COLUMNS = [
    "Account", "Coin", "Execution Price", "Size Tokens", "Size USD", "Side",
    "Timestamp IST", "Start Position", "Direction", "Closed PnL", "Fee",
]


def load_trades(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Load trades and attach a ``date`` column parsed from the IST timestamp.

    The export writes ``dd-mm-YYYY HH:MM``. Parsing it explicitly rather than
    letting pandas infer stops 01-02-2024 silently becoming January the 2nd.
    """
    frame = pd.read_csv(path, usecols=columns or USED_COLUMNS)
    frame["time_ist"] = pd.to_datetime(frame["Timestamp IST"], format="%d-%m-%Y %H:%M")
    frame["date"] = frame["time_ist"].dt.date
    return frame
