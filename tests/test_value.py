import numpy as np
import pandas as pd
import pytest

from ppa_italia.value import capture_price, capture_rate, yearly_summary


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
