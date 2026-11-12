"""Tiny deterministic per-zone data directory for tests (synthetic, but distinct per zone)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ppa_italia.zones import ZONES


def _bell(index: pd.DatetimeIndex) -> np.ndarray:
    """Clear-sky-like daytime bell centred on 11 UTC, zero at night, stronger in summer."""
    hour = index.hour.to_numpy() + 0.0
    day = np.clip(np.cos((hour - 11.0) / 6.0 * np.pi / 2.0), 0.0, None)
    season = 0.65 + 0.35 * np.cos((index.dayofyear.to_numpy() - 172) / 365.0 * 2.0 * np.pi)
    return day * season


def make_fixture_dir(path: Path, years=(2023, 2024)) -> Path:
    """Write every per-zone data file for all 7 zones into `path` and return it.

    Prices: base 80 + 5 x zone index, minus a midday dip, plus seeded noise. Zonal solar: the bell
    scaled by 1000 + 100 x zone index MW. Imbalance: price +/- noise on one side, 0 on the other.
    Site profile: weather years 2005-2006, MWh per MWp. Also writes manifest.json.
    """
    path.mkdir(parents=True, exist_ok=True)
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-31 23:00", freq="h", tz="UTC", name="utc_hour")
    site_idx = pd.date_range("2005-01-01", "2006-12-31 23:00", freq="h", tz="UTC", name="utc_hour")
    files: dict[str, dict] = {}

    def write(name: str, frame: pd.DataFrame) -> None:
        frame.to_parquet(path / name)
        files[name] = {
            "source": "fixture",
            "first": str(frame.index.min()),
            "last": str(frame.index.max()),
            "rows": len(frame),
        }

    for i, zone in enumerate(ZONES):
        rng = np.random.default_rng(i)
        bell = _bell(idx)
        price = 80.0 + 5.0 * i - 30.0 * bell + rng.normal(0.0, 5.0, len(idx))
        write(f"prices_{zone}.parquet", pd.DataFrame({"price": price}, index=idx))
        write(f"solar_zone_{zone}.parquet", pd.DataFrame({"mw": bell * (1000.0 + 100.0 * i)}, index=idx))
        noise = rng.normal(0.0, 10.0, len(idx))
        short = noise > 0  # one side non-zero per hour, as in the Italian single-price rows
        write(
            f"imbalance_{zone}.parquet",
            pd.DataFrame(
                {"positive": np.where(short, price + noise, 0.0), "negative": np.where(short, 0.0, price + noise)},
                index=idx,
            ),
        )
        site = _bell(site_idx) * (0.85 + 0.01 * i)  # MWh per MWp
        write(f"site_{zone}.parquet", pd.DataFrame({"mwh_per_mwp": site}, index=site_idx))

    (path / "manifest.json").write_text(json.dumps({"built": "fixture", "files": files}, indent=2))
    return path
