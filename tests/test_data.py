import numpy as np
import pandas as pd
import pytest
import requests

from ppa_italia.data import pvgis, store
from ppa_italia.data.entsoe import capacity_for_year, fill_short_gaps, to_hourly
from ppa_italia.data.pvgis import parse_hourly
from ppa_italia.data.synthetic import make_synthetic_prices


def test_to_hourly_averages_quarter_hours():
    idx = pd.date_range("2025-10-01 00:00", periods=8, freq="15min", tz="Europe/Rome")
    s = to_hourly(pd.Series([10, 20, 30, 40, 0, 0, 0, 4], index=idx, dtype=float))
    assert list(s.values) == [25.0, 1.0]
    assert str(s.index.tz) == "UTC"


def test_parse_pvgis_hourly():
    s = parse_hourly([{"time": "20230601:1010", "P": 2_000_000.0}, {"time": "20230601:1110", "P": 0.0}])
    assert s.iloc[0] == pytest.approx(2.0)
    assert s.index[0] == pd.Timestamp("2023-06-01 10:00", tz="UTC")


def test_synthetic_prices_shape():
    s = make_synthetic_prices(seed=0)
    assert str(s.index.tz) == "UTC"
    assert len(s) == len(pd.date_range("2021-01-01", "2025-12-31 23:00", freq="h", tz="UTC"))
    # midday solar dip: mean price 11-14 UTC below mean 17-20 UTC
    h = s.index.hour
    assert s[(h >= 11) & (h <= 14)].mean() < s[(h >= 17) & (h <= 20)].mean()
    assert (make_synthetic_prices(seed=0) == s).all()  # deterministic
    assert (s >= 0).all()


def test_load_prices_falls_back_to_synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PRECOMPUTED", tmp_path)
    s, synthetic = store.load_prices("SUD")
    assert synthetic is True and len(s) > 0


def test_load_prices_reads_parquet(tmp_path, monkeypatch):
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    pd.Series([1.0, 2.0, 3.0], index=idx, name="price").to_frame().to_parquet(tmp_path / "prices_SUD.parquet")
    monkeypatch.setattr(store, "PRECOMPUTED", tmp_path)
    monkeypatch.delenv("SUNDIAL_FORCE_SYNTHETIC", raising=False)
    s, synthetic = store.load_prices("SUD")
    assert synthetic is False and list(s) == [1.0, 2.0, 3.0]


def test_load_wind_cf_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PRECOMPUTED", tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load_wind_cf("SUD")


def test_load_solar_puglia_is_hourly_series():
    s = store.load_solar_puglia()
    assert isinstance(s, pd.Series) and len(s) > 0 and str(s.index.tz) == "UTC"


def test_pvgis_error_on_http_failure(monkeypatch):
    class R:
        def raise_for_status(self): raise requests.HTTPError("400")
    monkeypatch.setattr(pvgis.requests, "get", lambda *a, **k: R())
    with pytest.raises(pvgis.PvgisError):
        pvgis.fetch_hourly_pv(0.0, -30.0, 1000, 2020, 2020)


def _cap(years, values):
    return pd.Series(values, index=pd.DatetimeIndex([f"{y}-01-01" for y in years], tz="Europe/Rome"), dtype=float)


def test_capacity_for_year_picks_that_year():
    assert capacity_for_year(_cap([2023, 2024, 2025], [10, 20, 30]), 2024) == 20.0


def test_capacity_for_year_falls_back_to_earlier():
    assert capacity_for_year(_cap([2023], [10]), 2024) == 10.0


def test_capacity_for_year_raises_when_none_earlier():
    with pytest.raises(ValueError):
        capacity_for_year(_cap([2026], [10]), 2024)


def test_fill_short_gaps_interpolates_up_to_limit():
    idx = pd.date_range("2024-01-01", periods=12, freq="h", tz="UTC")
    s = pd.Series(np.arange(12, dtype=float), index=idx).drop(idx[[2, 3, 8, 9, 10]])
    # gap of 2 hours (2,3) and gap of 3 hours (8,9,10); hour 11 stays as the last value
    filled, n = fill_short_gaps(s, max_hours=6)
    assert n == 5
    assert len(filled) == 12 and filled.isna().sum() == 0
    assert filled.iloc[2] == pytest.approx(2.0) and filled.iloc[9] == pytest.approx(9.0)


def test_fill_short_gaps_leaves_long_gaps_missing():
    idx = pd.date_range("2024-01-01", periods=20, freq="h", tz="UTC")
    s = pd.Series(np.arange(20, dtype=float), index=idx).drop(idx[4:12])  # gap of 8 hours
    filled, n = fill_short_gaps(s, max_hours=6)
    assert n == 0
    assert len(filled) == 20 and filled.isna().sum() == 8


def test_fill_short_gaps_gap_of_exactly_six_is_filled():
    idx = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
    s = pd.Series([0.0] + [np.nan] * 6 + [7.0, 8.0, 9.0], index=idx).dropna()
    filled, n = fill_short_gaps(s, max_hours=6)
    assert n == 6 and filled.isna().sum() == 0 and filled.iloc[3] == pytest.approx(3.0)


def test_force_synthetic_env_ignores_real_price_files(tmp_path, monkeypatch):
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    pd.Series([1.0, 2.0, 3.0], index=idx, name="price").to_frame().to_parquet(tmp_path / "prices_SUD.parquet")
    monkeypatch.setattr(store, "PRECOMPUTED", tmp_path)
    monkeypatch.setenv("SUNDIAL_FORCE_SYNTHETIC", "1")
    _, synthetic = store.load_prices("SUD")
    assert synthetic is True
