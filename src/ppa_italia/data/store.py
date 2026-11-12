"""Load precomputed data files, with a synthetic fallback for prices."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from ppa_italia.data.synthetic import make_synthetic_prices

PRECOMPUTED = Path(__file__).resolve().parents[3] / "data" / "precomputed"


def load_prices(zone: str) -> tuple[pd.Series, bool]:
    """Return (hourly UTC prices in EUR/MWh, is_synthetic) for a bidding zone.

    Setting the env var SUNDIAL_FORCE_SYNTHETIC=1 ignores real price files (used by the tests).
    """
    path = PRECOMPUTED / f"prices_{zone}.parquet"
    if path.exists() and os.environ.get("SUNDIAL_FORCE_SYNTHETIC") != "1":
        return pd.read_parquet(path)["price"], False
    return make_synthetic_prices(), True


def load_solar_puglia() -> pd.Series:
    """Return hourly UTC production (MWh) of the 20 MWp Puglia solar park."""
    return pd.read_parquet(PRECOMPUTED / "puglia_solar.parquet")["gen_mwh"]


def load_wind_cf(zone: str) -> pd.Series:
    """Return the hourly wind capacity factor (0..1) for a zone.

    Raises FileNotFoundError if scripts/build_wind_proxy.py has not been run.
    """
    path = PRECOMPUTED / f"wind_cf_{zone}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run scripts/build_wind_proxy.py")
    return pd.read_parquet(path)["cf"]
