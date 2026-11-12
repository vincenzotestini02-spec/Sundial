"""Build the precomputed data directory from ENTSO-E data, via the File Library or the API.

Both sources produce the same per-zone hourly UTC series and go through ``write_zone_files``,
so they write identical files:

    prices_{zone}.parquet        column ``price``  (EUR/MWh, day-ahead)
    solar_zone_{zone}.parquet    column ``mw``     (actual solar generation)
    imbalance_{zone}.parquet     column ``price``  (single imbalance price, EUR/MWh)
    site_{zone}.parquet          column ``mwh_per_mwp`` (PVGIS, 1 MWp at the zone's site)
    manifest.json                source, build time, first/last timestamp and rows per file
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ppa_italia.data import entsoe, file_library
from ppa_italia.data.pvgis import fetch_hourly_pv
from ppa_italia.zones import ZONE_SITE


def _write_series(series_by_zone: dict[str, pd.Series], prefix: str, column: str, out_dir: Path,
                  files: dict) -> None:
    """Gap-fill each zone's series, write ``{prefix}_{zone}.parquet`` and record it in ``files``."""
    for zone, s in series_by_zone.items():
        if s is None or s.empty:
            continue
        filled, _ = entsoe.fill_short_gaps(s)
        filled = filled.rename(column).rename_axis(None)
        name = f"{prefix}_{zone}.parquet"
        filled.to_frame().to_parquet(out_dir / name)
        files[name] = {"first": filled.index[0].isoformat(), "last": filled.index[-1].isoformat(),
                       "rows": int(len(filled))}


def write_zone_files(prices: dict[str, pd.Series], solar: dict[str, pd.Series],
                     imbalance: dict[str, pd.Series], out_dir: Path, source: str) -> dict:
    """Gap-fill (up to 6 hours) and write the per-zone files and ``manifest.json``; return the manifest.

    Entries of an existing manifest for files not rewritten in this call are kept.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    files = json.loads(manifest_path.read_text())["files"] if manifest_path.exists() else {}
    _write_series(prices, "prices", "price", out_dir, files)
    _write_series(solar, "solar_zone", "mw", out_dir, files)
    _write_series(imbalance, "imbalance", "price", out_dir, files)
    manifest = {"source": source, "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "files": files}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def write_site_profiles(out_dir: Path, start_year: int = 2005, end_year: int = 2023) -> None:
    """Fetch PVGIS hourly output for 1 MWp at each zone's representative site; write ``site_{zone}.parquet``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for zone, (_, lat, lon) in ZONE_SITE.items():
        gen, _ = fetch_hourly_pv(lat, lon, 1000, start_year, end_year)
        gen.rename("mwh_per_mwp").rename_axis(None).to_frame().to_parquet(out_dir / f"site_{zone}.parquet")


def build_from_file_library(price_zips: list[Path], solar_zips: list[Path], imbalance_zips: list[Path],
                            zones: list[str], start_month: str, out_dir: Path) -> dict:
    """Build from File Library zips (a kind with no zips is skipped); return the manifest."""
    prices = file_library.read_prices(price_zips, zones, start_month) if price_zips else {}
    solar = file_library.read_generation_zones(solar_zips, zones, "Solar", start_month) if solar_zips else {}
    imbalance = file_library.read_imbalance(imbalance_zips, zones, start_month) if imbalance_zips else {}
    return write_zone_files(prices, solar, imbalance, out_dir, "file-library")


def build_from_api(client, zones: list[str], start: str, end: str, out_dir: Path) -> dict:
    """Build from the ENTSO-E API through an ``EntsoePandasClient``-like ``client``; return the manifest."""
    return write_zone_files(
        entsoe.api_prices(zones, start, end, client),
        entsoe.api_solar(zones, start, end, client),
        entsoe.api_imbalance(zones, start, end, client),
        out_dir, "api",
    )
