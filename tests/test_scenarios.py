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


# --- same-year scenarios -------------------------------------------------

from ppa_italia.scenarios import build_scenarios_same_year  # noqa: E402


def _shaped(y, peak_hour, scale=1.0):
    """A year whose single maximum sits at `peak_hour` (hour of year, non-leap numbering)."""
    s = _year(y, 1.0)
    s = s.copy()
    s.iloc[peak_hour] = 10.0 * scale
    return s * scale


def _prices_2y():
    rng = np.random.default_rng(0)
    parts = [pd.Series(50 + rng.random(len(_year(y))) * 20, index=_year(y).index) for y in (2023, 2024)]
    return pd.concat(parts)


def _site_2w():
    return pd.concat([_shaped(2005, 100, 1.0), _shaped(2006, 200, 2.0)])


def test_same_year_shape_and_energy():
    zone = pd.concat([_shaped(2023, 300), _shaped(2024, 500)])
    site = _site_2w()
    sc, fallback = build_scenarios_same_year(_prices_2y(), zone, site, mwp=20, level=80.0)
    assert sc.prices.shape == (4, 8760) and fallback == []
    assert sc.labels == [(2023, 2005), (2023, 2006), (2024, 2005), (2024, 2006)]
    e = {w: v.sum() for w, v in to_8760(site).items()}
    assert sc.gen[0].sum() == pytest.approx(e[2005] * 20)
    assert sc.gen[1].sum() == pytest.approx(e[2006] * 20)
    assert np.argmax(sc.gen[0]) == 300
    assert np.argmax(sc.gen[2]) == 500


def test_missing_zone_year_falls_back_to_site_shape():
    zone = _shaped(2023, 300)
    sc, fallback = build_scenarios_same_year(_prices_2y(), zone, _site_2w(), mwp=20)
    assert fallback == [2024] and sc.prices.shape[0] == 4
    # median-energy weather year (lower-middle of two) is 2005, peak at hour 100
    assert np.argmax(sc.gen[2]) == 100


def test_none_zone_solar_falls_back_for_all_years():
    _, fallback = build_scenarios_same_year(_prices_2y(), None, _site_2w(), mwp=20)
    assert fallback == [2023, 2024]


def test_partial_current_year_is_excluded():
    prices = pd.concat([_prices_2y(), _year(2025).iloc[:744]])
    sc, _ = build_scenarios_same_year(prices, None, _site_2w(), mwp=20, level=70.0)
    assert sorted({p for p, _ in sc.labels}) == [2023, 2024]


def test_long_nan_gap_in_zone_year_falls_back_but_short_gap_is_filled():
    z23 = _shaped(2023, 300)
    z24 = _shaped(2024, 500)
    z23.iloc[1000:1010] = np.nan  # 10 h > 6 h: cannot be repaired
    z24.iloc[2000:2003] = np.nan  # 3 h: filled
    sc, fallback = build_scenarios_same_year(_prices_2y(), pd.concat([z23, z24]), _site_2w(), mwp=20)
    assert fallback == [2023]
    assert not np.isnan(sc.gen).any()
    assert np.argmax(sc.gen[2]) == 500


def test_price_year_with_nan_is_excluded():
    prices = _prices_2y()
    prices.iloc[10] = np.nan
    sc, _ = build_scenarios_same_year(prices, None, _site_2w(), mwp=20, level=70.0)
    assert sorted({p for p, _ in sc.labels}) == [2024]


def test_same_year_all_nan_zone_solar_falls_back_everywhere():
    zone = pd.concat([_year(y, np.nan) for y in (2023, 2024)])
    sc, fallback = build_scenarios_same_year(_prices_2y(), zone, _site_2w(), mwp=20, level=80.0)
    assert fallback == [2023, 2024] and sc.prices.shape[0] == 4
