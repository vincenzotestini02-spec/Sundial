"""Hourly solar production for a site from PVGIS (EU JRC). Free, no API key.

Source: PVGIS (c) European Union, 2001-2026. Cite in every chart and deliverable.
API docs: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
"""
from __future__ import annotations

import pandas as pd
import requests

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


class PvgisError(Exception):
    """Raised when PVGIS cannot be reached or returns an unusable response."""


def fetch_hourly_pv(
    lat: float,
    lon: float,
    peak_kw: float,
    start_year: int,
    end_year: int,
    loss_pct: float = 14.0,
    timeout: int = 120,
) -> tuple[pd.Series, dict]:
    """Return (hourly production in MWh indexed by UTC hour, PVGIS input metadata).

    Raises PvgisError on HTTP error, timeout, or a response without ``outputs.hourly``.

    Uses PVGIS-optimised fixed tilt and azimuth. PVGIS timestamps look like
    ``20230101:0010`` (UTC, minute = sun-position offset); they are floored to the hour.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": peak_kw,
        "loss": loss_pct,
        "pvcalculation": 1,
        "optimalangles": 1,
        "startyear": start_year,
        "endyear": end_year,
        "outputformat": "json",
    }
    try:
        r = requests.get(PVGIS_URL, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return parse_hourly(data["outputs"]["hourly"]), data["inputs"]
    except (requests.RequestException, ValueError, KeyError) as err:
        raise PvgisError(f"PVGIS request failed or returned no hourly data: {err!r}") from err


def parse_hourly(hourly: list[dict]) -> pd.Series:
    idx = pd.to_datetime([h["time"] for h in hourly], format="%Y%m%d:%H%M", utc=True).floor("h")
    # P is in W for the requested peak power -> MWh per hour
    values = [h["P"] / 1e6 for h in hourly]
    return pd.Series(values, index=idx, name="gen_mwh")
