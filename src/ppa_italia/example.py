"""The per-zone solar example case: scenarios, illustrative offers and market assumptions."""
import csv
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from ppa_italia.data import store
from ppa_italia.imbalance import imbalance_cost
from ppa_italia.pricing import fair_floor_premium
from ppa_italia.scenarios import ScenarioSet, build_scenarios_same_year, profile_on_years
from ppa_italia.structures import Market, Offer

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "default"


@dataclass(frozen=True)
class ExampleCase:
    """Everything the analysis needs for the example plant."""

    scenarios: ScenarioSet
    offers: list[Offer]
    market: Market
    is_synthetic: bool
    horizon: int  # years; the longest offer tenor
    capacity_mw: float = 20.0
    zone: str = "SUD"
    status: store.DataStatus | None = None
    fallback_years: list[int] = field(default_factory=list)  # price years on the PVGIS shape
    imbalance_source: str = "placeholder"  # "computed" or "placeholder"


def _read_offers(sc: ScenarioSet, avg_gen_mw: float) -> tuple[list[Offer], dict[str, float], dict[str, float]]:
    """Read offers.csv, pricing each relative to the P50 capture or the baseload level.

    Returns the offers (floor premium still 0), and per offer name the premium as a
    percentage of the fair floor premium and the balancing fee as a percentage of
    the imbalance cost.
    """
    p50_capture = float(np.percentile(sc.capture_prices(), 50))
    bases = {"capture": p50_capture, "baseload": sc.reference_level}
    offers, premium_pct, fee_pct = [], {}, {}
    with open(EXAMPLE_DIR / "offers.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            offers.append(Offer(
                name=row["name"],
                structure=row["structure"],
                price=float(row["price_pct"]) / 100 * bases[row["price_basis"]],
                tenor_years=int(row["tenor_years"]),
                indexation_pct=float(row["indexation_pct"]),
                imbalance_on_buyer=row["imbalance_on_buyer"] == "true",
                goo_included=row["goo_included"] == "true",
                zero_volume_negative=row["zero_volume_negative"] == "true",
                rating=row["rating"],
                penalty_severity=int(row["penalty_severity"]),
                baseload_mw=float(row["baseload_pct_of_avg_mw"]) / 100 * avg_gen_mw,
                floor_premium=0.0,  # set from the fair premium once the market is known
            ))
            premium_pct[row["name"]] = float(row["floor_premium_pct_of_fair"])
            fee_pct[row["name"]] = float(row["balancing_fee_pct_of_cost"])
    return offers, premium_pct, fee_pct


def _solar_shape(zone: str, zone_solar: pd.Series | None, prices: pd.Series) -> pd.Series:
    """Hourly solar shape for weighting the imbalance cost: the zone's real solar, else the site profile on the price years."""
    if zone_solar is not None and len(zone_solar.dropna()):
        return zone_solar
    return profile_on_years(store.load_site_profile(zone), sorted(set(prices.index.year)))


def _apply_costs(o: Offer, sc: ScenarioSet, premium_pct: float, fee: float) -> Offer:
    """Add the data-derived costs to an anchored offer (EUR/MWh on contracted volume).

    Floor: premium = premium_pct of the fair premium, plus the balancing fee.
    Pay-as-produced and baseload: the balancing fee the buyer charges for taking
    the imbalance is deducted from the price. The fee applies only when the buyer
    takes the imbalance (`imbalance_on_buyer`); otherwise the seller keeps it and
    pays no fee.
    """
    if not o.imbalance_on_buyer:
        fee = 0.0
    if o.structure == "floor":
        return replace(o, floor_premium=fair_floor_premium(o, sc) * premium_pct / 100 + fee)
    return replace(o, price=o.price - fee)


def load_example(zone: str = "SUD", capacity_mw: float = 20.0) -> ExampleCase:
    """Build the example case for `zone` from the zone's data files and the CSV/TOML files.

    Offer prices are anchored to the P50 capture or baseload level; the floor premium
    is a percentage of the fair premium; the imbalance cost is computed from the
    zone's imbalance prices when present, otherwise the TOML placeholder is used.
    Scenarios cover three price levels (current baseload and +/- `price_level_band`
    around it, a stated assumption in the TOML), so the P50/P10 statistics and CVaR
    include price-level risk.
    """
    prices, is_synthetic = store.load_prices(zone)
    zone_solar = store.load_zone_solar(zone)
    with open(EXAMPLE_DIR / "assumptions.toml", "rb") as f:
        assumptions = tomllib.load(f)
    band = assumptions.pop("price_level_band")  # not a Market field
    market = Market(**assumptions)
    sc, fallback = build_scenarios_same_year(
        prices, zone_solar, store.load_site_profile(zone), capacity_mw,
        level_factors=(1 - band, 1.0, 1 + band),
    )
    offers, premium_pct, fee_pct = _read_offers(sc, float(sc.gen.mean()))
    imbalance = store.load_imbalance(zone)
    source = "placeholder"
    if imbalance is not None:
        cost = imbalance_cost(imbalance, prices, _solar_shape(zone, zone_solar, prices), market.imbalance_error_share)
        market = replace(market, imbalance_cost=cost)
        source = "computed"
    offers = [_apply_costs(o, sc, premium_pct[o.name], fee_pct[o.name] / 100 * market.imbalance_cost) for o in offers]
    return ExampleCase(
        scenarios=sc,
        offers=offers,
        market=market,
        is_synthetic=is_synthetic,
        horizon=max(o.tenor_years for o in offers),
        capacity_mw=capacity_mw,
        zone=zone,
        status=store.data_status(zone),
        fallback_years=fallback,
        imbalance_source=source,
    )
