import numpy as np
import pandas as pd
import pytest

from trader_sentiment.stats import (
    dunn_posthoc,
    kruskal_across_groups,
    normality_by_group,
    significant_pairs,
)


@pytest.fixture
def separated():
    """Three bands with genuinely different, heavy-tailed PnL distributions."""
    rng = np.random.default_rng(42)
    frames = []
    for name, centre in [("Fear", 60.0), ("Neutral", 30.0), ("Greed", 5.0)]:
        frames.append(pd.DataFrame({
            "sentiment": name,
            "Closed PnL": rng.standard_t(df=2, size=400) * 5 + centre,
        }))
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def identical():
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "sentiment": ["Fear"] * 300 + ["Greed"] * 300,
        "Closed PnL": rng.normal(0, 1, 600),
    })


def test_heavy_tailed_pnl_is_reported_as_non_normal(separated):
    out = normality_by_group(separated)
    assert len(out) == 3
    assert not out["normal"].any()      # which is why the rest is rank-based


def test_shapiro_is_sampled_down_to_stay_meaningful():
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"sentiment": "Fear", "Closed PnL": rng.normal(size=20_000)})
    out = normality_by_group(big, limit=5000)
    assert out.loc[0, "n"] == 5000


def test_kruskal_finds_a_real_difference(separated):
    out = kruskal_across_groups(separated)
    assert out["groups"] == 3
    assert out["significant"] is True
    assert out["p_value"] < 0.001


def test_kruskal_does_not_invent_a_difference_that_is_not_there(identical):
    out = kruskal_across_groups(identical)
    assert out["significant"] is False


def test_kruskal_needs_something_to_compare(separated):
    with pytest.raises(ValueError, match="at least two groups"):
        kruskal_across_groups(separated[separated.sentiment == "Fear"])


def test_dunn_is_symmetric_and_diagonal_is_one(separated):
    matrix = dunn_posthoc(separated)
    assert matrix.shape == (3, 3)
    assert np.allclose(np.diag(matrix), 1.0)
    assert np.allclose(matrix.to_numpy(), matrix.to_numpy().T)


def test_bonferroni_makes_the_pair_test_stricter_not_looser(separated):
    corrected = dunn_posthoc(separated, adjust="bonferroni")
    raw = dunn_posthoc(separated, adjust=None)
    assert (corrected.to_numpy() >= raw.to_numpy() - 1e-12).all()


def test_significant_pairs_reports_each_pair_once(separated):
    pairs = significant_pairs(dunn_posthoc(separated))
    assert len(pairs) == 3                      # 3 groups -> 3 unique pairs
    assert len({frozenset(p[:2]) for p in pairs}) == 3
    assert all(p < 0.05 for _, _, p in pairs)
