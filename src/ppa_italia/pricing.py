"""Indicative pay-as-produced PPA pricing and an honest backtest.

Seller's view of a pay-as-produced (PaP) PPA, all in EUR/MWh:

    fair PaP price = expected capture price
                     - imbalance cost (if the seller keeps balancing responsibility)
                     - profile/volume risk discount
                     - buyer margin
                     + GoO value (if guarantees of origin are transferred to the buyer)

Every input is an assumption documented with its source in docs/methodology.md.
Indicative only: not trading advice and not any company's pricing.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ppa_italia.value import yearly_summary


@dataclass(frozen=True)
class PapAssumptions:
    imbalance_cost: float = 0.0
    risk_discount: float = 0.0
    margin: float = 0.0
    goo_value: float = 0.0
    goo_transferred: bool = True


def fair_pap_price(expected_capture: float, a: PapAssumptions) -> float:
    goo = a.goo_value if a.goo_transferred else 0.0
    return expected_capture - a.imbalance_cost - a.risk_discount - a.margin + goo


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
