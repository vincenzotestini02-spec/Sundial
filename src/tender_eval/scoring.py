"""Multi-criteria scoring of PPA offers, with a weight-robustness check.

A tender evaluator's recommendation is only as good as its weights. Instead of
grading our own pick, we test it: perturb the weights thousands of times
(Dirichlet sampling around the chosen weights) and report how often each offer
still ranks first. A recommendation that wins in <70% of draws is flagged fragile.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def normalise(df: pd.DataFrame, higher_is_better: dict[str, bool]) -> pd.DataFrame:
    """Min-max scale each criterion to 0..1 where 1 is best."""
    out = pd.DataFrame(index=df.index)
    for col, hib in higher_is_better.items():
        lo, hi = df[col].min(), df[col].max()
        scaled = (df[col] - lo) / (hi - lo) if hi > lo else pd.Series(1.0, index=df.index)
        out[col] = scaled if hib else 1 - scaled
    return out


def score(df: pd.DataFrame, weights: dict[str, float], higher_is_better: dict[str, bool]) -> pd.Series:
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()
    return (normalise(df, higher_is_better)[w.index] * w).sum(axis=1).sort_values(ascending=False)


def rank_stability(
    df: pd.DataFrame,
    weights: dict[str, float],
    higher_is_better: dict[str, bool],
    n: int = 5000,
    concentration: float = 20.0,
    seed: int = 0,
) -> pd.Series:
    """Share of perturbed-weight draws in which each offer ranks first."""
    rng = np.random.default_rng(seed)
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()
    norm = normalise(df, higher_is_better)[w.index].to_numpy()
    draws = rng.dirichlet(w.to_numpy() * concentration, size=n)
    winners = (norm @ draws.T).argmax(axis=0)
    counts = np.bincount(winners, minlength=len(df))
    return pd.Series(counts / n, index=df.index, name="win_share").sort_values(ascending=False)
