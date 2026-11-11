"""The single headline recommendation: which offer, how much, at what fair price."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ppa_italia.hedge import cvar, max_cvar, merchant_breakeven_price, optimise_allocation
from ppa_italia.pricing import fair_price_range
from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer, npv
from ppa_italia.tender import (
    DEFAULT_WEIGHTS,
    FRAGILE_THRESHOLD,
    HIGHER_IS_BETTER,
    criteria_table,
    rank_stability,
    score,
)


@dataclass
class Recommendation:
    """One answer: sign `offer` for `share` of production, fair price fair_low-fair_mid.

    breakeven is offer-specific: for a floor offer it is the floor level at which
    the offer matches merchant on mean NPV.
    """

    offer: str
    share: float
    fair_low: float
    fair_mid: float
    breakeven: float
    win_share: float
    fragile: bool
    multi_offer_shares: dict[str, float]
    disagrees: bool
    cvar_floor: float


def recommend(
    offers: list[Offer],
    sc: ScenarioSet,
    m: Market,
    horizon: int,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    cvar_floor: float | None = None,
) -> Recommendation:
    """Run the full chain: score, robustness, hedge share, fair price, break-even.

    Default floor (cvar_floor=None), a stated and adjustable assumption: halve
    the gap between the all-merchant downside and the best downside the winning
    offer can deliver, i.e. merchant_cvar + 0.5 * (max_cvar(winner) - merchant_cvar).
    Pass cvar_floor explicitly to override (e.g. the merchant CVaR itself).
    """
    table = criteria_table(offers, sc, m, horizon)
    winner = score(table, weights, HIGHER_IS_BETTER).index[0]
    win_share = float(rank_stability(table, weights, HIGHER_IS_BETTER)[winner])

    npv_merchant = npv(None, sc, m, horizon)
    winner_offer = next(o for o in offers if o.name == winner)
    npv_winner = npv(winner_offer, sc, m, horizon)
    if cvar_floor is None:
        merchant_cvar = cvar(npv_merchant, m.cvar_alpha)
        best_cvar = max_cvar(npv_winner[:, None], npv_merchant, m.cvar_alpha)
        cvar_floor = merchant_cvar + 0.5 * (best_cvar - merchant_cvar)
    single = optimise_allocation(npv_winner[:, None], npv_merchant, cvar_floor, m.cvar_alpha)
    share = float(single.shares[0])

    npv_all = np.column_stack([npv(o, sc, m, horizon) for o in offers])
    multi = optimise_allocation(npv_all, npv_merchant, cvar_floor, m.cvar_alpha)
    multi_offer_shares = {o.name: float(s) for o, s in zip(offers, multi.shares)}
    top = max(multi_offer_shares, key=multi_offer_shares.get)
    disagrees = top != winner and multi_offer_shares[top] > 1e-6

    fair_low, fair_mid = fair_price_range(sc.capture_prices(), m, goo_transferred=True)

    try:
        breakeven = merchant_breakeven_price(winner_offer, sc, m, horizon)
    except ValueError:
        breakeven = float("nan")  # no break-even price in (0, 1000]; the app shows "n/a"

    return Recommendation(
        offer=winner,
        share=share,
        fair_low=fair_low,
        fair_mid=fair_mid,
        breakeven=breakeven,
        win_share=win_share,
        fragile=win_share < FRAGILE_THRESHOLD,
        multi_offer_shares=multi_offer_shares,
        disagrees=disagrees,
        cvar_floor=float(cvar_floor),
    )
