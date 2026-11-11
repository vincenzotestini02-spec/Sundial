"""Indicative pay-as-produced PPA price range and an honest backtest.

Fair price = P50 capture - imbalance cost - margin (+ GoO value if transferred),
with the low end shifted down by the P50-P10 capture gap. Every input is an
assumption documented in docs/methodology.md. Indicative only: not trading advice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_italia.structures import Market
from ppa_italia.value import yearly_summary


def fair_price_range(capture_by_scenario: np.ndarray, m: Market, goo_transferred: bool = True) -> tuple[float, float]:
    """Fair pay-as-produced price range (low, mid) in EUR/MWh.

    mid = P50 capture - imbalance cost - margin (+ GoO value if transferred);
    low = mid minus the gap between the P50 and P10 capture price.
    """
    cap = np.asarray(capture_by_scenario, dtype=float)
    p50 = float(np.percentile(cap, 50))
    p10 = float(np.percentile(cap, 10))
    goo = m.goo_value if goo_transferred else 0.0
    mid = p50 - m.imbalance_cost - m.margin + goo
    return mid - (p50 - p10), mid


def p_levels(values: pd.Series) -> dict[str, float]:
    """P50 / P90 in the seller's sense: P90 is exceeded in 90% of cases (10th percentile)."""
    v = np.asarray(values, dtype=float)
    return {"P50": float(np.percentile(v, 50)), "P90": float(np.percentile(v, 10))}


def backtest_trailing_capture(prices: pd.Series, gen: pd.Series) -> pd.DataFrame:
    """Naive forecast check: predict next year's capture price with this year's.

    This is the outside judge for the pricing anchor: the error column is what a
    customer would have gained or lost had they signed at the trailing estimate.
    """
    s = yearly_summary(prices, gen)[["capture_eur_mwh"]]
    s["forecast_from_prior_year"] = s["capture_eur_mwh"].shift(1)
    s["error_eur_mwh"] = s["capture_eur_mwh"] - s["forecast_from_prior_year"]
    return s.dropna()
