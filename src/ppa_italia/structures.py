"""PPA offers, market assumptions and the revenue a producer earns under each structure."""
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ppa_italia.scenarios import HOURS, ScenarioSet

RATINGS = ("AAA", "AA", "A", "BBB", "BB", "B")
STRUCTURES = ("pap", "baseload", "floor")


@dataclass(frozen=True)
class Offer:
    """One PPA offer. Percentages are decimals (0.02 = 2%)."""

    name: str
    structure: Literal["pap", "baseload", "floor"]
    price: float  # EUR/MWh; the floor level when structure == "floor"
    tenor_years: int
    indexation_pct: float
    imbalance_on_buyer: bool
    goo_included: bool
    zero_volume_negative: bool
    rating: str
    penalty_severity: int  # 1 mild ... 5 severe
    baseload_mw: float = 0.0
    floor_premium: float = 0.0  # EUR/MWh paid by the producer for the floor

    def __post_init__(self):
        if self.structure not in STRUCTURES:
            raise ValueError(f"structure must be one of {STRUCTURES}, got {self.structure!r}")
        if self.tenor_years < 1:
            raise ValueError("tenor_years must be >= 1")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.rating not in RATINGS:
            raise ValueError(f"rating must be one of {RATINGS}, got {self.rating!r}")
        if self.penalty_severity not in range(1, 6):
            raise ValueError("penalty_severity must be between 1 and 5")
        if self.structure == "baseload" and self.baseload_mw <= 0:
            raise ValueError("baseload_mw must be > 0 for a baseload structure")
        if self.floor_premium < 0:
            raise ValueError("floor_premium must be >= 0")


@dataclass(frozen=True)
class Market:
    """Market assumptions shared by all offers. Percentages are decimals."""

    imbalance_cost: float  # EUR/MWh
    goo_value: float  # EUR/MWh
    margin: float  # EUR/MWh
    discount_rate: float = 0.07
    merchant_escalation_pct: float = 0.0
    lgd: float = 0.6
    cvar_alpha: float = 0.10


def _spot(sc: ScenarioSet, m: Market, year: int) -> np.ndarray:
    """Scenario prices escalated to contract year `year`."""
    return sc.prices * (1 + m.merchant_escalation_pct) ** year


def merchant_revenue(sc: ScenarioSet, m: Market, year: int = 0) -> np.ndarray:
    """Revenue (EUR, shape (n,)) of selling everything at spot."""
    p = _spot(sc, m, year)
    total_gen = sc.gen.sum(axis=1)
    return (p * sc.gen).sum(axis=1) - m.imbalance_cost * total_gen + m.goo_value * total_gen


def offer_revenue(o: Offer, sc: ScenarioSet, m: Market, year: int = 0) -> np.ndarray:
    """Revenue (EUR, shape (n,)) of contract year `year` under offer `o`."""
    p = _spot(sc, m, year)
    g = sc.gen
    total_gen = g.sum(axis=1)
    price = o.price * (1 + o.indexation_pct) ** year

    if o.structure == "pap":
        volume = np.where(p <= 0, 0.0, g) if o.zero_volume_negative else g
        revenue = price * volume.sum(axis=1)
    elif o.structure == "baseload":
        revenue = price * o.baseload_mw * HOURS + (p * (g - o.baseload_mw)).sum(axis=1)
    else:  # floor: max(spot, floor) on contracted volume, premium per contracted MWh
        volume = np.where(p <= 0, 0.0, g) if o.zero_volume_negative else g
        revenue = (np.maximum(p, price) * volume).sum(axis=1) - o.floor_premium * volume.sum(axis=1)

    if not o.imbalance_on_buyer:
        revenue = revenue - m.imbalance_cost * total_gen
    if not o.goo_included:
        revenue = revenue + m.goo_value * total_gen
    return revenue


def npv(o: Offer | None, sc: ScenarioSet, m: Market, horizon: int) -> np.ndarray:
    """NPV (EUR, shape (n,)) over `horizon` years, discounted at year end.

    The offer pays for its tenor, merchant revenue follows. `o=None` is merchant throughout.
    """
    total = np.zeros(sc.prices.shape[0])
    for t in range(horizon):
        if o is not None and t < o.tenor_years:
            revenue = offer_revenue(o, sc, m, t)
        else:
            revenue = merchant_revenue(sc, m, t)
        total += revenue / (1 + m.discount_rate) ** (t + 1)
    return total
