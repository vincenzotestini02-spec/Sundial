import numpy as np
import pandas as pd
import pytest

from ppa_italia.pricing import PapAssumptions, backtest_trailing_capture, fair_pap_price, p_levels


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
