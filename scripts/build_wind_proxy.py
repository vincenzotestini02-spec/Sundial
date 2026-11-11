"""Build an hourly onshore-wind capacity-factor proxy per zone from ENTSO-E actual generation.

CF = hourly generation (MW) / installed capacity (MW) of that year, clipped to [0, 1].
Usage: ENTSOE_TOKEN=... python scripts/build_wind_proxy.py --zones SUD SICI --start 2021-01-01 --end 2025-12-31
Output: data/precomputed/wind_cf_{zone}.parquet (index UTC hour, column cf).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from ppa_italia.data.entsoe import ZONES, capacity_for_year, make_client, to_hourly

ROOT = Path(__file__).resolve().parents[1]
WIND_ONSHORE = "B19"


def _as_series(x: pd.Series | pd.DataFrame) -> pd.Series:
    """entsoe-py may return a DataFrame; reduce it to a Series, preferring "Actual Aggregated"."""
    if isinstance(x, pd.DataFrame):
        return x["Actual Aggregated"] if "Actual Aggregated" in x.columns else x.iloc[:, 0]
    return x


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zones", nargs="+", default=["SUD", "SICI"])
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    args = ap.parse_args()
    try:
        client = make_client()
    except RuntimeError as err:
        sys.exit(str(err))

    out = ROOT / "data" / "precomputed"
    out.mkdir(parents=True, exist_ok=True)
    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    for zone in args.zones:
        area, parts = ZONES[zone], []
        for year in range(start.year, end.year + 1):
            y0 = max(start, pd.Timestamp(year, 1, 1)).tz_localize("Europe/Rome")
            y1 = min(end + pd.Timedelta(days=1), pd.Timestamp(year + 1, 1, 1)).tz_localize("Europe/Rome")
            gen = to_hourly(_as_series(client.query_generation(area, start=y0, end=y1, psr_type=WIND_ONSHORE)))
            cap = _as_series(client.query_installed_generation_capacity(
                area, start=pd.Timestamp(year, 1, 1, tz="Europe/Rome"), end=pd.Timestamp(year + 1, 1, 1, tz="Europe/Rome"),
                psr_type=WIND_ONSHORE,
            ))
            installed = capacity_for_year(cap, year)
            parts.append((gen / installed).clip(0, 1))
            print(f"{zone} {year}: {len(gen)} hours, installed {installed:,.0f} MW")
        cf = pd.concat(parts)
        cf = cf[~cf.index.duplicated()].sort_index().rename("cf").rename_axis("utc_hour")
        cf.to_frame().to_parquet(out / f"wind_cf_{zone}.parquet")


if __name__ == "__main__":
    main()
