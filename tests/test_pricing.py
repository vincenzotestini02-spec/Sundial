import numpy as np
import pandas as pd
import pytest

from ppa_italia.pricing import backtest_trailing_capture, fair_price_range, p_levels
from ppa_italia.structures import Market


def test_fair_price_range_hand_computed():
    cap = np.arange(1.0, 101.0)  # P50 = 50.5, P10 = 10.9
    m = Market(imbalance_cost=3.0, goo_value=1.0, margin=2.0)
    low, mid = fair_price_range(cap, m)
    assert mid == pytest.approx(50.5 - 3 - 2 + 1)
    assert low == pytest.approx(mid - (50.5 - 10.9))


def test_p90_is_below_p50():
    lv = p_levels(pd.Series(range(1, 101)))
    assert lv["P90"] < lv["P50"]


def test_backtest_shifts_one_year():
    idx = pd.date_range("2022-01-01", "2024-12-31 23:00", freq="h", tz="UTC")
    prices = pd.Series(np.where(idx.year == 2022, 100.0, np.where(idx.year == 2023, 80.0, 60.0)), index=idx)
    bt = backtest_trailing_capture(prices, pd.Series(1.0, index=idx))
    assert list(bt.index) == [2023, 2024]
    assert list(bt["error_eur_mwh"].round(6)) == [-20.0, -20.0]
