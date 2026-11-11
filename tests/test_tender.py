import numpy as np
import pandas as pd
import pytest

from ppa_italia.tender import (
    DEFAULT_WEIGHTS,
    FRAGILE_THRESHOLD,
    HIGHER_IS_BETTER,
    criteria_table,
    rank_stability,
    score,
)
from ppa_italia.structures import npv
from tests.helpers import M0, _flat_sc, _offer


OFFERS = pd.DataFrame(
    {"price": [72.0, 68.0, 70.0], "tenor": [10, 12, 7], "credit": [3, 5, 4]},
    index=["A", "B", "C"],
)
HIB = {"price": True, "tenor": True, "credit": True}


def test_score_and_stability():
    w = {"price": 0.6, "tenor": 0.2, "credit": 0.2}
    assert score(OFFERS, w, HIB).index[0] == "A"
    stab = rank_stability(OFFERS, w, HIB, n=2000)
    assert stab.sum() == pytest.approx(1.0)
    assert stab.index[0] == "A"


def test_dominant_offer_is_always_stable():
    df = pd.DataFrame({"price": [80.0, 60.0], "tenor": [12, 8]}, index=["best", "worse"])
    stab = rank_stability(df, {"price": 1, "tenor": 1}, {"price": True, "tenor": True}, n=500)
    assert stab["best"] == 1.0


def test_criteria_table_columns_and_values():
    sc = _flat_sc(50.0)
    offers = [_offer(name="hi", price=70.0), _offer(name="lo", price=40.0)]
    t = criteria_table(offers, sc, M0, horizon=10)
    assert list(t.columns) == list(HIGHER_IS_BETTER)
    assert t.loc["hi", "npv_mean"] > t.loc["lo", "npv_mean"]
    assert t.loc["lo", "credit_el"] == 0.0
    assert score(t, DEFAULT_WEIGHTS, HIGHER_IS_BETTER).index[0] == "hi"


def test_criteria_table_index_and_npv_p10():
    sc = _flat_sc(50.0, n=20)
    o = _offer(name="pap_a", price=55.0)
    t = criteria_table([o], sc, M0, horizon=10)
    assert list(t.index) == ["pap_a"]
    assert t.index.name == "name"
    values = npv(o, sc, M0, 10)
    assert t.loc["pap_a", "npv_mean"] == pytest.approx(values.mean())
    assert t.loc["pap_a", "npv_p10"] == pytest.approx(np.percentile(values, 10))


def test_criteria_table_copies_offer_terms_and_casts_imbalance():
    sc = _flat_sc(50.0)
    o = _offer(name="terms", tenor_years=7, indexation_pct=0.02,
               imbalance_on_buyer=False, penalty_severity=4)
    t = criteria_table([o], sc, M0, horizon=10)
    assert t.loc["terms", "tenor_years"] == 7
    assert t.loc["terms", "indexation_pct"] == pytest.approx(0.02)
    assert t.loc["terms", "penalty_severity"] == 4
    assert t.loc["terms", "imbalance_on_buyer"] == 0
    assert t["imbalance_on_buyer"].dtype.kind in "iu"


def test_fragile_threshold_and_default_weights():
    assert FRAGILE_THRESHOLD == 0.70
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(DEFAULT_WEIGHTS) == set(HIGHER_IS_BETTER)
