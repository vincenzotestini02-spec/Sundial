"""Buyer credit expected loss on a PPA.

PD_ANNUAL: long-run average one-year corporate default rates, S&P Global Ratings
annual default study - verify against the latest edition and update the citation.
"""
import numpy as np

from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer, merchant_revenue, offer_revenue

PD_ANNUAL = {"AAA": 0.0000, "AA": 0.0002, "A": 0.0005, "BBB": 0.0015, "BB": 0.0060, "B": 0.0300}


def expected_credit_loss(o: Offer, sc: ScenarioSet, m: Market) -> float:
    """Present value (EUR) of expected loss from buyer default.

    Exposure at contract year t is the mean over scenarios of the positive part of
    the PV (at t) of the remaining years' (offer - merchant) revenue: the seller
    only loses if the contract is worth more than selling at spot. Loss in year t
    is weighted by the marginal default probability (1-pd)^t * pd, times LGD,
    discounted to today.
    """
    pd = PD_ANNUAL[o.rating]
    gap = [offer_revenue(o, sc, m, k) - merchant_revenue(sc, m, k) for k in range(o.tenor_years)]
    loss = 0.0
    for t in range(o.tenor_years):
        pv_remaining = sum(gap[k] / (1 + m.discount_rate) ** (k - t) for k in range(t, o.tenor_years))
        exposure = float(np.mean(np.maximum(0.0, pv_remaining)))
        loss += (1 - pd) ** t * pd * m.lgd * exposure / (1 + m.discount_rate) ** t
    return float(loss)
