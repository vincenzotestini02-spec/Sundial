import pandas as pd
import pytest

from ppa_italia.data.entsoe import to_hourly
from ppa_italia.data.pvgis import parse_hourly


def test_to_hourly_averages_quarter_hours():
    idx = pd.date_range("2025-10-01 00:00", periods=8, freq="15min", tz="Europe/Rome")
    s = to_hourly(pd.Series([10, 20, 30, 40, 0, 0, 0, 4], index=idx, dtype=float))
    assert list(s.values) == [25.0, 1.0]
    assert str(s.index.tz) == "UTC"


def test_parse_pvgis_hourly():
    s = parse_hourly([{"time": "20230601:1010", "P": 2_000_000.0}, {"time": "20230601:1110", "P": 0.0}])
    assert s.iloc[0] == pytest.approx(2.0)
    assert s.index[0] == pd.Timestamp("2023-06-01 10:00", tz="UTC")
