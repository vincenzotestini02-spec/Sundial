"""Synthetic Italian zonal day-ahead prices, used when real ENTSO-E data is not built."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_prices(start: str = "2021-01-01", end: str = "2025-12-31 23:00", seed: int = 0) -> pd.Series:
    """Return hourly UTC prices in EUR/MWh with a stylised duck-curve shape.

    Base 100, plus 25 at 17-20 UTC (evening peak), minus a midday dip at 11-14 UTC that
    deepens linearly from 10 (2021) to 40 (2025) and is scaled by month (1.0 in May-Aug,
    0.6 in Apr/Sep, 0.3 otherwise). Gaussian noise (sigma 15) from a seeded generator;
    floored at 0. Deterministic for a given seed.
    """
    idx = pd.date_range(start, end, freq="h", tz="UTC")
    hour = idx.hour
    price = np.full(len(idx), 100.0)
    price += np.where((hour >= 17) & (hour <= 20), 25.0, 0.0)
    depth = 10.0 + (idx.year - 2021) * 7.5  # 10 -> 40 over 2021-2025
    month_scale = np.where((idx.month >= 5) & (idx.month <= 8), 1.0, np.where(np.isin(idx.month, [4, 9]), 0.6, 0.3))
    price -= np.where((hour >= 11) & (hour <= 14), depth * month_scale, 0.0)
    price += np.random.default_rng(seed).normal(0.0, 15.0, len(idx))
    return pd.Series(np.maximum(price, 0.0), index=idx, name="price")
