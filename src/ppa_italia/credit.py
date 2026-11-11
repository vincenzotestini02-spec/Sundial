"""Buyer credit expected loss on a PPA.

PD_ANNUAL: long-run average one-year corporate default rates, S&P Global Ratings
annual default study - verify against the latest edition and update the citation.
"""
import numpy as np

from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer, merchant_revenue, npv, offer_revenue

PD_ANNUAL = {"AAA": 0.0000, "AA": 0.0002, "A": 0.0005, "BBB": 0.0015, "BB": 0.0060, "B": 0.0300}


def expected_credit_loss(o: Offer, sc: ScenarioSet, m: Market) -> float:
    """Present value (EUR) of expected loss from buyer default.

    Timing follows npv(): revenue of contract year k is booked at the end of year k.
    If the buyer defaults during year t, the seller loses years t..T-1; the loss is
    recognised at the end of year t. Exposure is the mean over scenarios of the
    positive part of the PV (at end of year t) of the remaining (offer - merchant)
    revenue gaps: the seller only loses if the contract is worth more than spot.
    Each loss is weighted by the marginal default probability (1-pd)^t * pd, times
    LGD, and discounted (1+r)^(t+1) to today, so every gap is discounted (1+r)^(k+1)
    in total, as in npv().
    """
    pd = PD_ANNUAL[o.rating]
    r = m.discount_rate
    gap = [offer_revenue(o, sc, m, k) - merchant_revenue(sc, m, k) for k in range(o.tenor_years)]
    loss = 0.0
    for t in range(o.tenor_years):
        pv_remaining = sum(gap[k] / (1 + r) ** (k - t) for k in range(t, o.tenor_years))
        exposure = float(np.mean(np.maximum(0.0, pv_remaining)))
        loss += (1 - pd) ** t * pd * m.lgd * exposure / (1 + r) ** (t + 1)
    return float(loss)


def npv_net_of_credit(o: Offer | None, sc: ScenarioSet, m: Market, horizon: int) -> np.ndarray:
    """NPV per scenario (EUR, shape (n,)) minus the offer's expected credit loss (a scalar PV).

    This is the hedge objective (spec 5.5 step 3), shared by recommend() and the app so
    Home, Hedge and Report agree. `o=None` is merchant throughout and carries no credit loss.
    """
    values = npv(o, sc, m, horizon)
    if o is None:
        return values
    return values - expected_credit_loss(o, sc, m)
