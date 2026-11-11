import numpy as np
import pandas as pd
import pytest

from ppa_italia.scenarios import (
    build_scenarios,
    rescale_to_level,
    to_8760,
    trailing_baseload,
)


def _year(y, value=50.0):
    idx = pd.date_range(f"{y}-01-01", f"{y}-12-31 23:00", freq="h", tz="UTC")
    return pd.Series(value, index=idx)


def test_to_8760_drops_leap_day_and_partial_years():
    s = pd.concat([_year(2024), _year(2025).iloc[:100]])
    out = to_8760(s)
    assert list(out) == [2024] and out[2024].shape == (8760,)


def test_rescale_keeps_shape_and_sign():
    p = np.array([-10.0, 0.0, 50.0, 200.0])
    r = rescale_to_level(p, 60.0)
    assert r.mean() == pytest.approx(60.0)
    assert r[0] < 0 and r[1] == 0 and r[3] / r[2] == pytest.approx(4.0)


def test_rescale_rejects_non_positive_mean():
    with pytest.raises(ValueError):
        rescale_to_level(np.array([-5.0, 5.0]), 60.0)


def test_rescale_rejects_non_positive_level():
    with pytest.raises(ValueError):
        rescale_to_level(np.array([1.0, 2.0]), 0.0)


def test_trailing_baseload_uses_last_months_only():
    s = pd.concat([_year(2024, 100.0), _year(2025, 40.0)])
    assert trailing_baseload(s, months=12) == pytest.approx(40.0)


def test_build_scenarios_pairs_every_year():
    prices = pd.concat([_year(2022, 300.0), _year(2023, 100.0)])
    gen = pd.concat([_year(2010, 1.0), _year(2011, 2.0), _year(2012, 1.0)])
    sc = build_scenarios(prices, gen, level=80.0)
    assert sc.prices.shape == (6, 8760) and len(sc.labels) == 6
    assert sc.labels[0] == (2022, 2010) and sc.labels[1] == (2022, 2011)
    assert np.allclose(sc.prices.mean(axis=1), 80.0)  # 2022 crisis level removed
    assert np.allclose(sc.capture_prices(), 80.0)     # flat prices -> capture = level


def test_build_scenarios_default_level_is_trailing_baseload():
    prices = pd.concat([_year(2022, 300.0), _year(2023, 100.0)])
    sc = build_scenarios(prices, _year(2010, 1.0))
    assert sc.reference_level == pytest.approx(100.0)


def test_build_scenarios_requires_complete_years():
    with pytest.raises(ValueError):
        build_scenarios(_year(2025).iloc[:100], _year(2010))
    with pytest.raises(ValueError):
        build_scenarios(_year(2025), _year(2010).iloc[:100])


def _varied_gen():
    """Three weather years with different constant levels: 10, 20, 30 per hour."""
    return pd.concat([_year(2005, 10.0), _year(2006, 20.0), _year(2007, 30.0)])


def test_profile_on_years_covers_requested_years_hourly_utc():
    from ppa_italia.scenarios import profile_on_years
    out = profile_on_years(_varied_gen(), [2021, 2024])
    expected = pd.date_range("2021-01-01", "2021-12-31 23:00", freq="h", tz="UTC").append(
        pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz="UTC"))
    assert out.index.equals(expected)


def test_profile_on_years_uses_median_weather_year_energy():
    from ppa_italia.scenarios import profile_on_years
    out = profile_on_years(_varied_gen(), [2021, 2024])
    assert out[out.index.year == 2021].sum() == pytest.approx(20.0 * 8760)
    assert out[out.index.year == 2024].sum() == pytest.approx(20.0 * 8784)  # leap day = 28 Feb profile


def test_profile_on_years_even_count_takes_lower_middle():
    from ppa_italia.scenarios import profile_on_years
    gen = pd.concat([_year(2005, 10.0), _year(2006, 20.0), _year(2007, 30.0), _year(2008, 40.0)])
    out = profile_on_years(gen, [2022])
    assert out.sum() == pytest.approx(20.0 * 8760)


def test_profile_on_years_constant_profile_reproduces_constant():
    from ppa_italia.scenarios import profile_on_years
    out = profile_on_years(_year(2010, 7.0), [2021, 2022, 2024])
    assert (out == 7.0).all()
