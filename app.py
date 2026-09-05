"""Trader Sentiment Analysis — an interactive view of the finding.

Run locally:      streamlit run app.py
Deployed:         Streamlit Community Cloud, entry point app.py

The app fetches the Fear & Greed index from its public API on load. The trade
export is 47MB and is not in the repository, so when it is absent the app runs
in demo mode against a bundled summary rather than showing an error page — a
deployed link that greets a recruiter with a stack trace is worse than no link.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from trader_sentiment import analysis, clean, config, fear_greed, loaders  # noqa: E402
from trader_sentiment.config import SENTIMENT_ORDER  # noqa: E402

st.set_page_config(page_title="Trader Sentiment Analysis", page_icon="📊", layout="wide")

#: Precomputed from the full 167,331-trade dataset, so the deployed app has
#: something real to show when the export is not mounted. Reproduced by
#: `python -m trader_sentiment.build` followed by sql/contrarian_edge.sql.
DEMO_EDGE = pd.DataFrame({
    "sentiment": SENTIMENT_ORDER,
    "buy_pnl": [55.67, 64.81, 17.88, 35.01, 6.54],
    "sell_pnl": [24.20, 37.73, 42.37, 39.32, 71.73],
})
DEMO_EDGE["buy_minus_sell"] = DEMO_EDGE["buy_pnl"] - DEMO_EDGE["sell_pnl"]
DEMO_EDGE["favours"] = DEMO_EDGE["buy_minus_sell"].map(lambda d: "BUY" if d > 0 else "SELL")


@st.cache_data(ttl=3600)
def load_index() -> pd.DataFrame:
    return fear_greed.fetch(limit=0)


@st.cache_data
def load_edge() -> tuple[pd.DataFrame, bool]:
    """The real edge table if the export is present, otherwise the bundled one."""
    path = config.trades_csv()
    if not path.exists():
        return DEMO_EDGE.copy(), False
    trades = loaders.load_trades(path)
    cleaned, _ = clean.prepare(trades, fear_greed.load_or_fetch(config.fear_greed_csv()))
    return analysis.contrarian_edge(cleaned), True


st.title("Do traders actually make money being contrarian?")
st.caption(
    "Realised profit and loss on Hyperliquid trades, segmented by the Bitcoin "
    "Fear & Greed Index. Buy-minus-sell profit per sentiment band."
)

edge, live = load_edge()
if not live:
    st.info(
        "Running on the precomputed summary — the 47MB trade export is not bundled "
        "with the deployment. Every figure below comes from the full 167,331-trade "
        "dataset; clone the repo and run `python -m trader_sentiment.build` to "
        "reproduce it end to end.",
        icon="ℹ️",
    )

left, right = st.columns([3, 2])

with left:
    st.subheader("The contrarian edge, by sentiment band")
    st.caption(
        "Positive means buyers earned more than sellers that day. "
        "'Be greedy when others are fearful' predicts positive under fear, negative under greed."
    )
    st.bar_chart(edge.set_index("sentiment")["buy_minus_sell"], height=340)

with right:
    st.subheader("Average profit per trade")
    st.dataframe(
        edge.set_index("sentiment")[["buy_pnl", "sell_pnl", "buy_minus_sell", "favours"]]
        .round(2),
        use_container_width=True,
    )

fear = edge[edge.sentiment.isin(["Extreme Fear", "Fear"])]["buy_minus_sell"].mean()
greed = edge[edge.sentiment.isin(["Greed", "Extreme Greed"])]["buy_minus_sell"].mean()
a, b, c = st.columns(3)
a.metric("Fear days favour", "BUY", f"{fear:+.2f} avg edge")
b.metric("Greed days favour", "SELL", f"{greed:+.2f} avg edge")
c.metric("Trades analysed", "167,331", "32 accounts")

st.divider()

st.subheader("Bitcoin Fear & Greed Index, live")
st.caption("Fetched from the alternative.me public API, cached for an hour.")
try:
    index = load_index()
    recent = index.tail(365).copy()
    recent["date"] = pd.to_datetime(recent["date"])
    st.line_chart(recent.set_index("date")["value"], height=240)
    latest = index.iloc[-1]
    st.write(f"Latest reading: **{int(latest['value'])} — {latest['classification']}** "
             f"({latest['date']})")
except Exception as error:                                   # noqa: BLE001
    st.warning(f"Could not reach the Fear & Greed API: {error}")

st.divider()

st.subheader("What this does and does not show")
st.markdown(
    """
- **The band-level effect is real.** All ten pairwise comparisons survive a Bonferroni
  correction (Kruskal-Wallis H = 685.66, p ≈ 4e-147).
- **It is not a per-trade signal.** A classifier trained to call individual trades scores
  ROC-AUC **0.53** — barely better than a coin flip. Shifting an average is not the same
  as predicting a trade.
- **The effective sample is 32 accounts, not 167,331 trades.** The top account holds
  23.5% of all profit and the top five hold 62.6%, so this is closer to *"these traders
  did"* than *"traders do"*.
- **Fees do not erase it.** Costs consume 1.9–3.9% of average profit, against an edge of
  +31 under Extreme Fear.
- **Correlation, not causation**, at daily resolution, on one venue, with no
  out-of-sample test.
"""
)
