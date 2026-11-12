"""Read ENTSO-E File Library CSV extracts (monthly, all of Europe) without an API token.

Registered users can download monthly extracts from the Transparency Platform's File
Library (folders such as EnergyPrices_12.1.D_r3.1). A download bundles at most 100 files
in one zip. These helpers read the CSVs straight from one or more zips, keep only the
requested Italian bidding zones, and return hourly UTC series in the same shape as the
API loader in ``entsoe.py``.

Source: ENTSO-E Transparency Platform.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from ppa_italia.data.entsoe import fill_short_gaps, to_hourly

# EIC codes of the Italian bidding zones, as they appear in the AreaCode column.
IT_AREA_CODES = {
    "NORD": "10Y1001A1001A73I",
    "CNOR": "10Y1001A1001A70O",
    "CSUD": "10Y1001A1001A71M",
    "SUD": "10Y1001A1001A788",
    "CALA": "10Y1001C--00096J",
    "SICI": "10Y1001A1001A75E",
    "SARD": "10Y1001A1001A74G",
}


def _monthly_csvs(zip_paths: list[Path], start_month: str):
    """Yield (zip, member name) for every monthly CSV from start_month (YYYY_MM) onwards, in month order."""
    members = []
    for p in zip_paths:
        zf = zipfile.ZipFile(p)
        for name in zf.namelist():
            if name.endswith(".csv") and name[:7] >= start_month:
                members.append((name[:7], zf, name))
    for _, zf, name in sorted(members, key=lambda m: m[0]):
        yield zf, name


def _read_filtered(zf: zipfile.ZipFile, name: str, usecols: list[str], keep) -> pd.DataFrame:
    """Read one tab-separated CSV in chunks and keep only the rows where keep(chunk) is True."""
    parts = []
    with zf.open(name) as f:
        for chunk in pd.read_csv(f, sep="\t", usecols=usecols, chunksize=500_000):
            parts.append(chunk[keep(chunk)])
    return pd.concat(parts) if parts else pd.DataFrame(columns=usecols)


def _hourly(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Turn (DateTime(UTC), value) rows into an hourly UTC series, averaging sub-hourly steps."""
    s = pd.Series(
        df[value_col].astype(float).values,
        index=pd.to_datetime(df["DateTime(UTC)"]).dt.tz_localize("UTC"),
    )
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return to_hourly(s)


def read_prices(zip_paths: list[Path], zones: list[str], start_month: str = "2021_01") -> dict[str, pd.Series]:
    """Hourly day-ahead prices (EUR/MWh) per Italian zone from EnergyPrices_12.1.D zips."""
    codes = {zone: IT_AREA_CODES[zone] for zone in zones}  # KeyError for an unknown zone
    cols = ["DateTime(UTC)", "AreaCode", "ContractType", "Price[Currency/MWh]"]
    wanted = set(codes.values())
    frames = []
    for zf, name in _monthly_csvs(zip_paths, start_month):
        frames.append(_read_filtered(
            zf, name, cols,
            lambda c: c["AreaCode"].isin(wanted) & (c["ContractType"] == "Day-ahead"),
        ))
    rows = pd.concat(frames) if frames else pd.DataFrame(columns=cols)
    return {zone: _hourly(rows[rows["AreaCode"] == code], "Price[Currency/MWh]") for zone, code in codes.items()}


def read_generation(zip_paths: list[Path], zone: str, production_type: str = "Solar",
                    start_month: str = "2021_01") -> pd.Series:
    """Hourly actual generation (MW) of one production type in one Italian zone, from AggregatedGenerationPerType zips."""
    code = IT_AREA_CODES[zone]
    cols = ["DateTime(UTC)", "AreaCode", "ProductionType", "ActualGenerationOutput[MW]"]
    frames = []
    for zf, name in _monthly_csvs(zip_paths, start_month):
        frames.append(_read_filtered(
            zf, name, cols,
            lambda c: (c["AreaCode"] == code) & (c["ProductionType"] == production_type),
        ))
    rows = pd.concat(frames) if frames else pd.DataFrame(columns=cols)
    return _hourly(rows, "ActualGenerationOutput[MW]")


def build_from_zips(price_zips: list[Path], out_dir: Path, zones: list[str],
                    start_month: str = "2021_01") -> dict[str, tuple[int, int]]:
    """Write prices_{zone}.parquet (column 'price') for the app; return {zone: (hours, hours filled)}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for zone, s in read_prices(price_zips, zones, start_month).items():
        filled, n = fill_short_gaps(s)
        filled.rename("price").to_frame().to_parquet(out_dir / f"prices_{zone}.parquet")
        report[zone] = (len(filled), n)
    return report
