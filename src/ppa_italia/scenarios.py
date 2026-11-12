"""Price scenarios: historical hourly shape, rescaled to a current price level."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ppa_italia.data.entsoe import fill_short_gaps

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


def _complete_years(s: pd.Series) -> dict[int, np.ndarray]:
    """Like `to_8760`, but a year containing any NaN does not count as complete."""
    return {y: v for y, v in to_8760(s).items() if not np.isnan(v).any()}


def _median_energy_year(complete: dict[int, np.ndarray]) -> np.ndarray:
    """The year whose annual energy is the median (lower-middle when the count is even)."""
    by_energy = sorted(complete.items(), key=lambda kv: kv[1].sum())
    return by_energy[(len(by_energy) - 1) // 2][1]


def profile_on_years(gen: pd.Series, years: list[int]) -> pd.Series:
    """Stamp a typical (median-energy) weather year onto the given calendar years.

    The weather year whose annual energy is the median of the complete years is
    chosen (with an even count, the lower-middle one by sorted energy). Its
    8760-hour profile is repeated for every requested year as an hourly UTC
    Series. In leap years the 29 Feb hours repeat the profile of 28 Feb.
    """
    complete = to_8760(gen)
    if not complete:
        raise ValueError("no complete generation year (8760 hours) found")
    profile = _median_energy_year(complete)
    feb28_end = (31 + 28) * 24  # hours before 1 Mar in a non-leap year
    leap_profile = np.concatenate([profile[:feb28_end], profile[feb28_end - 24:feb28_end], profile[feb28_end:]])
    parts = []
    for year in sorted(set(years)):
        idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h", tz="UTC")
        parts.append(pd.Series(leap_profile if len(idx) == 8784 else profile, index=idx))
    return pd.concat(parts)


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
    reference_level: float  # central baseload level (the factor-1.0 rows are rescaled to it)
    level_factors: tuple[float, ...] | None = None  # price-level multipliers, if a band was used

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


def build_scenarios_same_year(
    prices: pd.Series,
    zone_solar: pd.Series | None,
    site_mwh_per_mwp: pd.Series,
    mwp: float,
    level: float | None = None,
    level_factors: tuple[float, ...] = (1.0,),
) -> tuple[ScenarioSet, list[int]]:
    """Pair each price year with the zone's solar shape of the SAME year.

    Method: prices and solar both depend on that year's weather and demand, so a
    price year is matched with the real zonal solar shape of that year (hourly
    MW divided by its annual sum, so it only describes *when* the sun produced).
    Short gaps (<= 6 h) in the zonal series are filled first; a year still
    incomplete (not 8760 hours, or any NaN) cannot give a shape, so that price
    year falls back to the site's median-energy PVGIS weather year, and is
    reported in the returned list. Price years that are partial or contain NaN
    are dropped.

    The energy level then comes from the site's PVGIS weather years: row
    (price year y, weather year w) has generation = shape_y x annual energy of
    weather year w x `mwp`. Prices are rescaled to `level` (default: trailing
    12-month baseload).

    Price-level band: history only tells us the *shape* of prices, not whether
    the whole market will sit higher or lower in future. So every row is
    repeated once per factor f in `level_factors`, with prices rescaled to
    `level x f` (e.g. (0.7, 1.0, 1.3) = the current level and 30% below/above
    it). This is a stated assumption, not a forecast; it is what gives a PPA
    something to hedge. Rows are ordered level first, then price year, then
    weather year. `reference_level` stays the central `level`.

    Returns the ScenarioSet (labels = (price_year, weather_year)) and the sorted
    list of price years that used the PVGIS fallback shape.
    """
    if level is None:
        level = trailing_baseload(prices)
    price_years = _complete_years(prices)
    site_years = _complete_years(site_mwh_per_mwp)
    if not price_years:
        raise ValueError("no complete price year (8760 hours) found")
    if not site_years:
        raise ValueError("no complete site weather year (8760 hours) found")

    zone_years: dict[int, np.ndarray] = {}
    if zone_solar is not None and len(zone_solar.dropna()):
        filled, _ = fill_short_gaps(zone_solar.dropna())
        zone_years = _complete_years(filled)
    fallback_shape = _median_energy_year(site_years)
    fallback_shape = fallback_shape / fallback_shape.sum()

    shapes, fallback = {}, []
    for price_year in price_years:
        zone = zone_years.get(price_year)
        if zone is not None and zone.sum() > 0:
            shapes[price_year] = zone / zone.sum()
        else:
            shapes[price_year] = fallback_shape
            fallback.append(price_year)

    price_rows, gen_rows, labels = [], [], []
    for factor in level_factors:
        for price_year, p in price_years.items():
            rescaled = rescale_to_level(p, level * factor)
            for weather_year, w in site_years.items():
                price_rows.append(rescaled)
                gen_rows.append(shapes[price_year] * w.sum() * mwp)
                labels.append((price_year, weather_year))
    sc = ScenarioSet(np.array(price_rows), np.array(gen_rows), labels, float(level), tuple(level_factors))
    return sc, fallback
