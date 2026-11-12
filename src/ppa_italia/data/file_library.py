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

from ppa_italia.data.entsoe import collapse_imbalance, to_hourly

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


def read_generation_zones(zip_paths: list[Path], zones: list[str], production_type: str = "Solar",
                          start_month: str = "2021_01") -> dict[str, pd.Series]:
    """Hourly actual generation (MW) of one production type per Italian zone, from AggregatedGenerationPerType zips.

    Each zip member is read once for all requested zones.
    """
    codes = {zone: IT_AREA_CODES[zone] for zone in zones}  # KeyError for an unknown zone
    cols = ["DateTime(UTC)", "AreaCode", "ProductionType", "ActualGenerationOutput[MW]"]
    wanted = set(codes.values())
    frames = []
    for zf, name in _monthly_csvs(zip_paths, start_month):
        frames.append(_read_filtered(
            zf, name, cols,
            lambda c: c["AreaCode"].isin(wanted) & (c["ProductionType"] == production_type),
        ))
    rows = pd.concat(frames) if frames else pd.DataFrame(columns=cols)
    return {zone: _hourly(rows[rows["AreaCode"] == code], "ActualGenerationOutput[MW]") for zone, code in codes.items()}


def read_generation(zip_paths: list[Path], zone: str, production_type: str = "Solar",
                    start_month: str = "2021_01") -> pd.Series:
    """Hourly actual generation (MW) of one production type in one Italian zone."""
    return read_generation_zones(zip_paths, [zone], production_type, start_month)[zone]


def read_imbalance(zip_paths: list[Path], zones: list[str], start_month: str = "2021_01") -> dict[str, pd.Series]:
    """Hourly single imbalance price (EUR/MWh) per Italian zone from ImbalancePrices_17.1.G zips.

    Italy publishes a positive and a negative price per quarter-hour, with 0.0 on the unused side.
    Per quarter-hour the non-zero side is taken (mean if both are non-zero, row dropped if both
    are zero), then averaged to hourly (spec section 8.1, see ``entsoe.collapse_imbalance``).
    """
    codes = {zone: IT_AREA_CODES[zone] for zone in zones}  # KeyError for an unknown zone
    pos_col, neg_col = "PositiveImbalancePrice[Currency/MWh]", "NegativeImbalancePrice[Currency/MWh]"
    cols = ["DateTime(UTC)", "AreaCode", pos_col, neg_col]
    wanted = set(codes.values())
    frames = [
        _read_filtered(zf, name, cols, lambda c: c["AreaCode"].isin(wanted))
        for zf, name in _monthly_csvs(zip_paths, start_month)
    ]
    rows = pd.concat(frames) if frames else pd.DataFrame(columns=cols)
    out = {}
    for zone, code in codes.items():
        part = rows[rows["AreaCode"] == code]
        idx = pd.to_datetime(part["DateTime(UTC)"]).dt.tz_localize("UTC")
        pos = pd.Series(part[pos_col].astype(float).values, index=idx)
        neg = pd.Series(part[neg_col].astype(float).values, index=idx)
        pos, neg = (x[~x.index.duplicated(keep="last")].sort_index() for x in (pos, neg))
        out[zone] = to_hourly(collapse_imbalance(pos, neg))
    return out
