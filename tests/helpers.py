"""Shared test helpers."""
import numpy as np

from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer


def _flat_sc(price=50.0, gen=1.0, n=1):
    return ScenarioSet(np.full((n, 8760), price), np.full((n, 8760), gen), [(2024, 2020)] * n, price)


M0 = Market(imbalance_cost=0.0, goo_value=0.0, margin=0.0)


def _offer(**kw):
    base = dict(name="X", structure="pap", price=60.0, tenor_years=10, indexation_pct=0.0,
                imbalance_on_buyer=True, goo_included=True, zero_volume_negative=False,
                rating="BBB", penalty_severity=3)
    return Offer(**{**base, **kw})
