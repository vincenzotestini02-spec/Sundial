"""Price scenarios: historical hourly shape, rescaled to a current price level."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

HOURS = 8760


def to_8760(s: pd.Series) -> dict[int, np.ndarray]:
    """Split an hourly series by calendar year, dropping 29 Feb.

    Only years with exactly 8760 hours left are kept.
    """
    is_leap_day = (s.index.month == 2) & (s.index.day == 29)
    s = s[~is_leap_day]
    out = {}
    for year, values in s.groupby(s.index.year):
        if len(values) == HOURS:
            out[int(year)] = values.to_numpy(dtype=float)
    return out


def rescale_to_level(year_prices: np.ndarray, level: float) -> np.ndarray:
    """Multiply a year of prices so that its mean equals `level`.

    Multiplying keeps the shape (and the sign of negative prices).
    """
    if level <= 0:
        raise ValueError("level must be > 0")
    mean = year_prices.mean()
    if mean <= 0:
        raise ValueError("price year mean must be > 0 to rescale")
    return year_prices * (level / mean)


def trailing_baseload(prices: pd.Series, months: int = 12) -> float:
    """Mean price over the last `months` months of data."""
    start = prices.index[-1] - pd.DateOffset(months=months)
    return float(prices[prices.index > start].mean())


@dataclass(frozen=True)
class ScenarioSet:
    """Paired price and generation scenarios, one row per (price year, weather year)."""

    prices: np.ndarray  # (n, 8760) EUR/MWh
    gen: np.ndarray  # (n, 8760) MWh
    labels: list[tuple[int, int]]  # (price_year, weather_year) per row
    reference_level: float  # baseload mean every price row was rescaled to

    def capture_prices(self) -> np.ndarray:
        """Generation-weighted average price of each scenario, shape (n,)."""
        return (self.prices * self.gen).sum(axis=1) / self.gen.sum(axis=1)


def build_scenarios(
    prices: pd.Series, gen: pd.Series, level: float | None = None
) -> ScenarioSet:
    """Pair every complete price year with every complete weather year.

    Each price year is rescaled to `level` (default: trailing 12-month baseload).
    Rows are ordered price year first, weather year second.
    """
    if level is None:
        level = trailing_baseload(prices)
    price_years = to_8760(prices)
    gen_years = to_8760(gen)
    if not price_years:
        raise ValueError("no complete price year (8760 hours) found")
    if not gen_years:
        raise ValueError("no complete generation year (8760 hours) found")

    price_rows, gen_rows, labels = [], [], []
    for price_year, p in price_years.items():
        rescaled = rescale_to_level(p, level)
        for weather_year, g in gen_years.items():
            price_rows.append(rescaled)
            gen_rows.append(g)
            labels.append((price_year, weather_year))
    return ScenarioSet(np.array(price_rows), np.array(gen_rows), labels, float(level))
