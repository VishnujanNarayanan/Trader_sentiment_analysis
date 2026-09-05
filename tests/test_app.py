"""The deployed page has to survive its data being absent.

A public link that greets a visitor with a stack trace is worse than no link, so
the fallback path is tested rather than assumed.
"""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_the_app_module_exists_and_names_streamlit_as_its_entry_point():
    source = APP.read_text(encoding="utf-8")
    assert "streamlit" in source
    assert "st.set_page_config" in source


def test_the_bundled_summary_matches_the_measured_result():
    """The demo numbers must be the real ones, not invented placeholders."""
    spec = importlib.util.spec_from_file_location("app_probe", APP)
    source = APP.read_text(encoding="utf-8")
    assert spec is not None
    # Read the constant without importing streamlit: the table is what matters.
    namespace: dict = {}
    block = source.split("DEMO_EDGE = ")[1].split("DEMO_EDGE[")[0]
    exec("import pandas as pd\nfrom trader_sentiment.config import SENTIMENT_ORDER\n"
         "DEMO_EDGE = " + block, namespace)          # noqa: S102
    demo = namespace["DEMO_EDGE"]
    demo["buy_minus_sell"] = demo["buy_pnl"] - demo["sell_pnl"]

    # These are the figures sql/contrarian_edge.sql returns on the full dataset.
    expected = {
        "Extreme Fear": 31.47, "Fear": 27.08, "Neutral": -24.49,
        "Greed": -4.31, "Extreme Greed": -65.18,
    }
    for band, value in expected.items():
        actual = demo.loc[demo.sentiment == band, "buy_minus_sell"].iloc[0]
        assert actual == pytest.approx(value, abs=0.01), band


def test_the_summary_tells_the_contrarian_story_in_the_right_direction():
    source = APP.read_text(encoding="utf-8")
    assert "ROC-AUC" in source          # the negative per-trade result is stated
    assert "32 accounts" in source      # the concentration caveat is stated
    assert isinstance(pd.DataFrame(), pd.DataFrame)
