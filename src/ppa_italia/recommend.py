"""The single headline recommendation: which offer, how much, at what fair price."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ppa_italia.credit import npv_net_of_credit
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


def _inside(best_cvar: float) -> float:
    """A CVaR level just below the best achievable one (relative margin 1e-6)."""
    return best_cvar - 1e-6 * abs(best_cvar)


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
    floor_capped: bool = False  # True when the target floor was above what the winner can achieve


def recommend(
    offers: list[Offer],
    sc: ScenarioSet,
    m: Market,
    horizon: int,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    cvar_floor: float | None = None,
) -> Recommendation:
    """Run the full chain: score, robustness, hedge share, fair price, break-even.

    Both LPs (winner alone and the multi-offer mix) use NPV net of each offer's
    expected credit loss. Default floor (cvar_floor=None), a stated and adjustable
    bank-style assumption: the average NPV in the worst 10% of scenarios must be at
    least `m.cvar_floor_share_of_mean` (0.85) times the expected merchant NPV.
    If the winner cannot reach that target, the floor is capped at the best CVaR it
    can deliver and `floor_capped` is True. If merchant CVaR already meets the floor,
    the hedge share is 0. Pass cvar_floor explicitly to override.
    """
    table = criteria_table(offers, sc, m, horizon)
    winner = score(table, weights, HIGHER_IS_BETTER).index[0]
    win_share = float(rank_stability(table, weights, HIGHER_IS_BETTER)[winner])

    npv_merchant = npv(None, sc, m, horizon)
    winner_offer = next(o for o in offers if o.name == winner)
    # Hedge objective: NPV net of the offer's expected credit loss (spec 5.5 step 3).
    npv_winner = npv_net_of_credit(winner_offer, sc, m, horizon)
    floor_capped = False
    best_cvar = max_cvar(npv_winner[:, None], npv_merchant, m.cvar_alpha)
    if cvar_floor is None:
        target = m.cvar_floor_share_of_mean * float(npv_merchant.mean())
        floor_capped = target > best_cvar
        cvar_floor = min(target, best_cvar)
    # Solve a hair inside the achievable boundary: at exactly best_cvar the LP can be reported
    # infeasible through solver tolerance. The reported cvar_floor stays the true target/cap.
    single = optimise_allocation(npv_winner[:, None], npv_merchant, min(cvar_floor, _inside(best_cvar)),
                                 m.cvar_alpha)
    if single.status != "optimal":
        raise RuntimeError(f"Hedge LP for offer {winner} is infeasible at CVaR floor {cvar_floor:,.0f}; "
                           f"cannot compute a hedge share.")
    share = float(single.shares[0])

    npv_all = np.column_stack([npv_net_of_credit(o, sc, m, horizon) for o in offers])
    multi = optimise_allocation(npv_all, npv_merchant, min(cvar_floor, _inside(
        max_cvar(npv_all, npv_merchant, m.cvar_alpha))), m.cvar_alpha)
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
        floor_capped=floor_capped,
    )
