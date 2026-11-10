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
