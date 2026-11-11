"""Multi-criteria scoring of PPA offers, with a weight-robustness check.

A tender evaluator's recommendation is only as good as its weights. Instead of
grading our own pick, we test it: perturb the weights thousands of times
(Dirichlet sampling around the chosen weights) and report how often each offer
still ranks first. A recommendation that wins in <70% of draws is flagged fragile.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_italia.credit import expected_credit_loss
from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer, npv

HIGHER_IS_BETTER = {
    "npv_mean": True,
    "npv_p10": True,
    "credit_el": False,
    "tenor_years": True,
    "indexation_pct": True,
    "imbalance_on_buyer": True,
    "penalty_severity": False,
}
DEFAULT_WEIGHTS = {
    "npv_mean": 0.30,
    "npv_p10": 0.20,
    "credit_el": 0.15,
    "tenor_years": 0.10,
    "indexation_pct": 0.05,
    "imbalance_on_buyer": 0.10,
    "penalty_severity": 0.10,
}
FRAGILE_THRESHOLD = 0.70


def criteria_table(offers: list[Offer], sc: ScenarioSet, m: Market, horizon: int) -> pd.DataFrame:
    """One row per offer with the criteria in HIGHER_IS_BETTER, indexed by offer name.

    NPV statistics come from the scenario distribution: `npv_mean` is the mean and
    `npv_p10` the 10th percentile (the downside). `credit_el` is the expected credit
    loss in EUR. Contract terms are copied from the offer, with `imbalance_on_buyer`
    cast to 0/1.
    """
    records = []
    for o in offers:
        values = npv(o, sc, m, horizon)
        records.append({
            "npv_mean": float(values.mean()),
            "npv_p10": float(np.percentile(values, 10)),
            "credit_el": expected_credit_loss(o, sc, m),
            "tenor_years": o.tenor_years,
            "indexation_pct": o.indexation_pct,
            "imbalance_on_buyer": int(o.imbalance_on_buyer),
            "penalty_severity": o.penalty_severity,
        })
    index = pd.Index([o.name for o in offers], name="name")
    return pd.DataFrame(records, index=index, columns=list(HIGHER_IS_BETTER))


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
