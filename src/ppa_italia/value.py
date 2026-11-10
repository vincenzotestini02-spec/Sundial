"""Capture price, capture rate and negative-price exposure.

All functions take two hourly pandas Series indexed by UTC timestamps:
- ``prices``: day-ahead price in EUR/MWh
- ``gen``: generation in MWh per hour (MW for hourly data)

Definitions (see docs/methodology.md):
- baseload price = simple mean of hourly prices
- capture price  = generation-weighted mean price = sum(p * g) / sum(g)
- capture rate   = capture price / baseload price
"""
from __future__ import annotations

import pandas as pd


def _align(prices: pd.Series, gen: pd.Series) -> pd.DataFrame:
    df = pd.concat({"price": prices, "gen": gen}, axis=1, join="inner").dropna()
    if df.empty:
        raise ValueError("prices and generation have no overlapping hours")
    if (df["gen"] < 0).any():
        raise ValueError("generation must be non-negative")
    return df


def capture_price(prices: pd.Series, gen: pd.Series) -> float:
    df = _align(prices, gen)
    total = df["gen"].sum()
    if total == 0:
        raise ValueError("zero total generation: capture price undefined")
    return float((df["price"] * df["gen"]).sum() / total)


def capture_rate(prices: pd.Series, gen: pd.Series) -> float:
    df = _align(prices, gen)
    return capture_price(df["price"], df["gen"]) / float(df["price"].mean())


def yearly_summary(prices: pd.Series, gen: pd.Series) -> pd.DataFrame:
    """One row per calendar year: baseload, capture price/rate, negative-price exposure."""
    df = _align(prices, gen)
    rows = []
    for year, g in df.groupby(df.index.year):
        total = g["gen"].sum()
        neg = g["price"] <= 0
        rows.append(
            {
                "year": year,
                "hours": len(g),
                "baseload_eur_mwh": g["price"].mean(),
                "capture_eur_mwh": (g["price"] * g["gen"]).sum() / total if total else float("nan"),
                "gen_mwh": total,
                "zero_or_negative_hours": int(neg.sum()),
                "gen_share_in_zero_or_negative_hours": g.loc[neg, "gen"].sum() / total if total else float("nan"),
            }
        )
    out = pd.DataFrame(rows).set_index("year")
    out["capture_rate"] = out["capture_eur_mwh"] / out["baseload_eur_mwh"]
    return out
