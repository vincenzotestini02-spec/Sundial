"""The Puglia solar example case: scenarios, illustrative offers and market assumptions."""
import csv
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ppa_italia.data import store
from ppa_italia.scenarios import ScenarioSet, build_scenarios, trailing_baseload
from ppa_italia.structures import Market, Offer

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "puglia"


@dataclass(frozen=True)
class ExampleCase:
    """Everything the analysis needs for the example plant."""

    scenarios: ScenarioSet
    offers: list[Offer]
    market: Market
    is_synthetic: bool
    horizon: int  # years; the longest offer tenor
    capacity_mw: float = 20.0


def _read_offers(sc: ScenarioSet, avg_gen_mw: float) -> list[Offer]:
    """Read offers.csv, pricing each relative to the P50 capture or the baseload level."""
    p50_capture = float(np.percentile(sc.capture_prices(), 50))
    bases = {"capture": p50_capture, "baseload": sc.reference_level}
    offers = []
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
                floor_premium=float(row["floor_premium"]),
            ))
    return offers


def load_example(zone: str = "SUD") -> ExampleCase:
    """Build the example case for `zone` from the bundled prices, solar profile and CSV/TOML files."""
    prices, is_synthetic = store.load_prices(zone)
    gen = store.load_solar_puglia()
    sc = build_scenarios(prices, gen, trailing_baseload(prices))
    offers = _read_offers(sc, float(gen.mean()))
    with open(EXAMPLE_DIR / "assumptions.toml", "rb") as f:
        market = Market(**tomllib.load(f))
    return ExampleCase(
        scenarios=sc,
        offers=offers,
        market=market,
        is_synthetic=is_synthetic,
        horizon=max(o.tenor_years for o in offers),
    )
