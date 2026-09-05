"""Is the gap between the bands real, or is it noise?

The notebook ran these tests in the right order but recorded neither the reason
for the order nor what the numbers licensed. The order matters: PnL is nowhere
near normal, which is precisely why the comparison has to be rank-based.
"""
from __future__ import annotations

import pandas as pd
from scipy import stats as scipy_stats

ALPHA = 0.05


def normality_by_group(trades: pd.DataFrame, value: str = "Closed PnL",
                       group: str = "sentiment", limit: int = 5000) -> pd.DataFrame:
    """Shapiro-Wilk per band.

    Shapiro's p-value is unreliable above a few thousand points, so each group is
    sampled down. This test is the justification for going non-parametric, not a
    result in its own right.
    """
    rows = []
    for name, chunk in trades.groupby(group):
        sample = chunk[value].dropna()
        if len(sample) > limit:
            sample = sample.sample(limit, random_state=42)
        if len(sample) < 3:
            continue
        statistic, p = scipy_stats.shapiro(sample)
        rows.append({group: name, "n": len(sample), "statistic": statistic,
                     "p_value": p, "normal": bool(p > ALPHA)})
    return pd.DataFrame(rows)


def kruskal_across_groups(trades: pd.DataFrame, value: str = "Closed PnL",
                          group: str = "sentiment") -> dict:
    """Kruskal-Wallis: do the bands differ at all?

    Rank-based, so it makes no normality assumption -- which the Shapiro results
    say is mandatory here.
    """
    groups = [chunk[value].dropna().to_numpy() for _, chunk in trades.groupby(group)]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        raise ValueError("need at least two groups to compare")
    statistic, p = scipy_stats.kruskal(*groups)
    return {"statistic": float(statistic), "p_value": float(p),
            "groups": len(groups), "significant": bool(p < ALPHA)}


def dunn_posthoc(trades: pd.DataFrame, value: str = "Closed PnL",
                 group: str = "sentiment", adjust: str = "bonferroni") -> pd.DataFrame:
    """Which specific pairs differ, with a correction for testing all of them.

    Kruskal says "somewhere"; it does not say where. Ten pairwise comparisons at
    5% would produce a false positive about 40% of the time uncorrected, hence
    Bonferroni.
    """
    import scikit_posthocs as sp

    frame = trades.dropna(subset=[value, group])
    return sp.posthoc_dunn(frame, val_col=value, group_col=group, p_adjust=adjust)


def significant_pairs(dunn: pd.DataFrame, alpha: float = ALPHA) -> list[tuple[str, str, float]]:
    """The pairs that survive correction, as ``(a, b, p)`` with a < b."""
    out = []
    for i, a in enumerate(dunn.index):
        for b in dunn.columns[i + 1:]:
            p = float(dunn.loc[a, b])
            if p < alpha:
                out.append((a, b, p))
    return sorted(out, key=lambda row: row[2])
