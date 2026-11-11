"""The single headline recommendation: which offer, how much, at what fair price."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ppa_italia.hedge import cvar, merchant_breakeven_price, optimise_allocation
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
    """One answer: sign `offer` for `share` of production, fair price fair_low-fair_mid."""

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

    cvar_floor=None means the all-merchant CVaR ("no worse in the bad years
    than not hedging").
    """
    table = criteria_table(offers, sc, m, horizon)
    winner = score(table, weights, HIGHER_IS_BETTER).index[0]
    win_share = float(rank_stability(table, weights, HIGHER_IS_BETTER)[winner])

    npv_merchant = npv(None, sc, m, horizon)
    if cvar_floor is None:
        cvar_floor = cvar(npv_merchant, m.cvar_alpha)

    winner_offer = next(o for o in offers if o.name == winner)
    npv_winner = npv(winner_offer, sc, m, horizon)
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
