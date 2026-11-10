import numpy as np
import pandas as pd
import pytest

from src.rtm_pricing.ppa import PapAssumptions, backtest_trailing_capture, fair_pap_price, p_levels
from src.tender_eval.scoring import rank_stability, score
from src.value_engine.capture import capture_price, capture_rate, yearly_summary
from src.value_engine.prices import to_hourly
from src.value_engine.pvgis import parse_hourly


def _hours(n, start="2024-01-01"):
    return pd.date_range(start, periods=n, freq="h", tz="UTC")


def test_capture_price_is_generation_weighted():
    idx = _hours(4)
    prices = pd.Series([100.0, 50.0, 0.0, 10.0], index=idx)
    gen = pd.Series([0.0, 1.0, 3.0, 0.0], index=idx)
    # (50*1 + 0*3) / 4 = 12.5 ; baseload = 40
    assert capture_price(prices, gen) == pytest.approx(12.5)
    assert capture_rate(prices, gen) == pytest.approx(12.5 / 40)


def test_flat_generation_has_capture_rate_one():
    idx = _hours(48)
    prices = pd.Series(np.random.default_rng(1).uniform(-5, 200, 48), index=idx)
    assert capture_rate(prices, pd.Series(1.0, index=idx)) == pytest.approx(1.0)


def test_rejects_bad_input():
    idx = _hours(2)
    with pytest.raises(ValueError):
        capture_price(pd.Series([1.0, 2.0], index=idx), pd.Series([0.0, 0.0], index=idx))
    with pytest.raises(ValueError):
        capture_price(pd.Series([1.0, 2.0], index=idx), pd.Series([-1.0, 1.0], index=idx))


def test_yearly_summary_counts_negative_hours():
    idx = _hours(4)
    prices = pd.Series([-1.0, 0.0, 30.0, 60.0], index=idx)
    gen = pd.Series([1.0, 1.0, 1.0, 1.0], index=idx)
    s = yearly_summary(prices, gen).loc[2024]
    assert s["zero_or_negative_hours"] == 2
    assert s["gen_share_in_zero_or_negative_hours"] == pytest.approx(0.5)


def test_to_hourly_averages_quarter_hours():
    idx = pd.date_range("2025-10-01 00:00", periods=8, freq="15min", tz="Europe/Rome")
    s = to_hourly(pd.Series([10, 20, 30, 40, 0, 0, 0, 4], index=idx, dtype=float))
    assert list(s.values) == [25.0, 1.0]
    assert str(s.index.tz) == "UTC"


def test_parse_pvgis_hourly():
    s = parse_hourly([{"time": "20230601:1010", "P": 2_000_000.0}, {"time": "20230601:1110", "P": 0.0}])
    assert s.iloc[0] == pytest.approx(2.0)
    assert s.index[0] == pd.Timestamp("2023-06-01 10:00", tz="UTC")


def test_fair_pap_price():
    a = PapAssumptions(imbalance_cost=3, risk_discount=5, margin=2, goo_value=1)
    assert fair_pap_price(80, a) == pytest.approx(71)
    assert fair_pap_price(80, PapAssumptions(goo_value=1, goo_transferred=False)) == pytest.approx(80)


def test_p90_is_below_p50():
    lv = p_levels(pd.Series(range(1, 101)))
    assert lv["P90"] < lv["P50"]


def test_backtest_shifts_one_year():
    idx = pd.date_range("2022-01-01", "2024-12-31 23:00", freq="h", tz="UTC")
    prices = pd.Series(np.where(idx.year == 2022, 100.0, np.where(idx.year == 2023, 80.0, 60.0)), index=idx)
    bt = backtest_trailing_capture(prices, pd.Series(1.0, index=idx))
    assert list(bt.index) == [2023, 2024]
    assert list(bt["error_eur_mwh"].round(6)) == [-20.0, -20.0]


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
