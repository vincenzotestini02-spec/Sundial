"""Load precomputed data files, with a synthetic fallback for prices."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ppa_italia.data.synthetic import make_synthetic_prices

PRECOMPUTED = Path(__file__).resolve().parents[3] / "data" / "precomputed"
_DEFAULT_DIR = PRECOMPUTED


def data_dir() -> Path:
    """Return the directory holding the precomputed files.

    Resolution order: a patched `PRECOMPUTED` (tests), then the env var SUNDIAL_DATA_DIR,
    then the repo default `data/precomputed`. Read at call time, never cached.
    """
    if PRECOMPUTED != _DEFAULT_DIR:
        return PRECOMPUTED
    override = os.environ.get("SUNDIAL_DATA_DIR")
    return Path(override) if override else _DEFAULT_DIR


@dataclass(frozen=True)
class DataStatus:
    """Which real data components exist for a zone."""

    prices_real: bool
    zone_solar: bool
    imbalance: bool


def load_prices(zone: str) -> tuple[pd.Series, bool]:
    """Return (hourly UTC prices in EUR/MWh, is_synthetic) for a bidding zone.

    Setting the env var SUNDIAL_FORCE_SYNTHETIC=1 ignores real price files (used by the tests).
    """
    path = data_dir() / f"prices_{zone}.parquet"
    if path.exists() and os.environ.get("SUNDIAL_FORCE_SYNTHETIC") != "1":
        return pd.read_parquet(path)["price"], False
    return make_synthetic_prices(), True


def load_zone_solar(zone: str) -> pd.Series | None:
    """Return the zone's hourly UTC solar generation in MW, or None if the file is missing."""
    path = data_dir() / f"solar_zone_{zone}.parquet"
    return pd.read_parquet(path)["mw"] if path.exists() else None


def load_imbalance(zone: str) -> pd.Series | None:
    """Return the zone's hourly UTC imbalance price (EUR/MWh), or None if the file is missing.

    The build step has already collapsed the ENTSO-E positive/negative columns into `price`.
    """
    path = data_dir() / f"imbalance_{zone}.parquet"
    return pd.read_parquet(path)["price"] if path.exists() else None


def load_site_profile(zone: str) -> pd.Series:
    """Return the hourly UTC PVGIS profile (MWh per MWp) of the zone's representative site.

    Raises FileNotFoundError naming the build command if the file is missing.
    """
    path = data_dir() / f"site_{zone}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run scripts/build_data.py")
    return pd.read_parquet(path)["mwh_per_mwp"]


def load_manifest() -> dict | None:
    """Return the parsed manifest.json of the data directory, or None if it does not exist."""
    path = data_dir() / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else None


def data_status(zone: str) -> DataStatus:
    """Report per component whether real data exists for a zone (prices honour SUNDIAL_FORCE_SYNTHETIC)."""
    return DataStatus(
        prices_real=not load_prices(zone)[1],
        zone_solar=load_zone_solar(zone) is not None,
        imbalance=load_imbalance(zone) is not None,
    )


def load_wind_cf(zone: str) -> pd.Series:
    """Return the hourly wind capacity factor (0..1) for a zone.

    Raises FileNotFoundError if the file is missing (wind is not built by the pipeline).
    """
    path = data_dir() / f"wind_cf_{zone}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: wind profiles are not built by scripts/build_data.py")
    return pd.read_parquet(path)["cf"]
