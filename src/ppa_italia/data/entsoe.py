"""Italian zonal day-ahead prices from the ENTSO-E Transparency Platform.

Requires a free API token: register on transparency.entsoe.eu, then email the
ENTSO-E helpdesk asking for "Restful API access". Put it in the ENTSOE_TOKEN env var.

Since the SDAC go-live of the 15-minute market time unit (delivery from 1 Oct 2025),
day-ahead prices come in 15-minute steps. They are averaged to hourly here so they
line up with hourly generation profiles (documented in docs/methodology.md).
"""
from __future__ import annotations

import os

import pandas as pd

# entsoe-py area codes for the zones used in this project
ZONES = {"NORD": "IT_NORD", "SUD": "IT_SUD", "SICI": "IT_SICI", "CSUD": "IT_CSUD", "CNOR": "IT_CNOR", "CALA": "IT_CALA", "SARD": "IT_SARD"}


def to_hourly(prices: pd.Series) -> pd.Series:
    """Average sub-hourly prices to hourly, UTC-indexed."""
    s = prices.copy()
    s.index = pd.DatetimeIndex(s.index).tz_convert("UTC")
    return s.resample("h").mean().dropna()


def fill_short_gaps(s: pd.Series, max_hours: int = 6) -> tuple[pd.Series, int]:
    """Reindex to a complete hourly UTC index and linearly fill gaps of <= max_hours.

    Longer gaps stay NaN. Returns the series and the number of hours filled.
    """
    full = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h", tz="UTC"))
    missing = full.isna()
    # run id of consecutive missing hours; run length per missing hour
    run_id = (missing != missing.shift()).cumsum()
    run_len = missing.groupby(run_id).transform("sum")
    fillable = missing & (run_len <= max_hours)
    interpolated = full.interpolate(method="linear", limit_area="inside")
    out = full.where(~fillable, interpolated)
    return out.rename(s.name), int(fillable.sum())


def collapse_imbalance(pos: pd.Series, neg: pd.Series) -> pd.Series:
    """Collapse a positive and a negative imbalance price into one price per period (spec section 8.1).

    Take the non-zero side; the mean if both are non-zero; drop periods where both are zero
    (or missing). Both series must share the same index.
    """
    pos, neg = pos.fillna(0.0), neg.fillna(0.0)
    both = (pos != 0) & (neg != 0)
    price = (pos + neg).where(~both, (pos + neg) / 2)
    return price[(pos != 0) | (neg != 0)]


def make_client(token: str | None = None):
    """Return an EntsoePandasClient; raise RuntimeError if no token is available."""
    token = token or os.environ.get("ENTSOE_TOKEN")
    if not token:
        raise RuntimeError("ENTSOE_TOKEN not set: see docs/data-sources.md for how to request one")
    from entsoe import EntsoePandasClient  # imported lazily so tests run without it

    return EntsoePandasClient(api_key=token)


def fetch_day_ahead(zone: str, start: str, end: str, token: str | None = None) -> pd.Series:
    """Return hourly UTC day-ahead prices (EUR/MWh) for a zone between start and end."""
    client = make_client(token)
    raw = client.query_day_ahead_prices(
        ZONES[zone], start=pd.Timestamp(start, tz="Europe/Rome"), end=pd.Timestamp(end, tz="Europe/Rome")
    )
    return to_hourly(raw).rename(f"da_{zone}")


def capacity_for_year(cap: pd.Series, year: int) -> float:
    """Return installed MW valid for ``year`` from a capacity series indexed by date.

    Uses the row whose index year equals ``year``, else the nearest earlier row.
    Raises ValueError if no row is dated on or before ``year``.
    """
    years = pd.DatetimeIndex(cap.index).year
    eligible = cap[years <= year]
    if eligible.empty:
        raise ValueError(f"no installed capacity on or before {year}")
    return float(eligible.sort_index().iloc[-1])


def _window(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return (start, end) as Europe/Rome timestamps for entsoe-py queries."""
    return pd.Timestamp(start, tz="Europe/Rome"), pd.Timestamp(end, tz="Europe/Rome")


def _per_zone(zones: list[str], query) -> dict[str, pd.Series]:
    """Run query(area_code) for each zone, skipping zones for which ENTSO-E has no data."""
    from entsoe.exceptions import NoMatchingDataError  # lazy: tests run without a token

    out = {}
    for zone in zones:
        try:
            out[zone] = query(ZONES[zone])
        except NoMatchingDataError:
            continue
    return out


def api_prices(zones: list[str], start: str, end: str, client) -> dict[str, pd.Series]:
    """Hourly UTC day-ahead prices (EUR/MWh) per zone via the API.

    ``client`` is an ``EntsoePandasClient`` (or a stub). Uses
    ``client.query_day_ahead_prices(area, start, end) -> pd.Series`` (tz-aware, 15-min or hourly).
    """
    s, e = _window(start, end)
    return _per_zone(zones, lambda area: to_hourly(client.query_day_ahead_prices(area, start=s, end=e)))


def api_solar(zones: list[str], start: str, end: str, client) -> dict[str, pd.Series]:
    """Hourly UTC actual solar generation (MW) per zone via the API.

    Uses ``client.query_generation(area, start, end, psr_type="B16") -> pd.DataFrame`` (B16 =
    solar). For one psr type entsoe-py returns a frame with a single column (``Solar``), or
    MultiIndex columns ``(Solar, Actual Aggregated)`` / ``(Solar, Actual Consumption)`` when
    consumption is also reported; the "Actual Aggregated" column is taken.
    """
    s, e = _window(start, end)

    def query(area):
        df = client.query_generation(area, start=s, end=e, psr_type="B16")
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs("Actual Aggregated", axis=1, level=-1)
        return to_hourly(df.iloc[:, 0])

    return _per_zone(zones, query)


def api_imbalance(zones: list[str], start: str, end: str, client) -> dict[str, pd.Series]:
    """Hourly UTC single imbalance price (EUR/MWh) per zone via the API.

    Uses ``client.query_imbalance_prices(area, start, end) -> pd.DataFrame`` with a tz-aware
    index and columns ``Long`` and ``Short`` (entsoe-py names for the two prices; for Italy one
    is 0.0 in each period). They are collapsed as in ``collapse_imbalance``.
    """
    s, e = _window(start, end)

    def query(area):
        df = client.query_imbalance_prices(area, start=s, end=e)
        return to_hourly(collapse_imbalance(df["Long"], df["Short"]))

    return _per_zone(zones, query)
