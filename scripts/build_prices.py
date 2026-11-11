"""Download ENTSO-E day-ahead prices per zone and store them as hourly parquet files.

Usage: ENTSOE_TOKEN=... python scripts/build_prices.py --zones NORD SUD SICI --start 2021-01-01 --end 2025-12-31
Output: data/precomputed/prices_{zone}.parquet (index UTC hour, column price, EUR/MWh).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from ppa_italia.data.entsoe import fetch_day_ahead, fill_short_gaps

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zones", nargs="+", default=["NORD", "SUD", "SICI"])
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    args = ap.parse_args()

    out = ROOT / "data" / "precomputed"
    out.mkdir(parents=True, exist_ok=True)
    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    for zone in args.zones:
        parts = []
        for year in range(start.year, end.year + 1):  # one request per year keeps responses small
            y0, y1 = max(start, pd.Timestamp(year, 1, 1)), min(end + pd.Timedelta(days=1), pd.Timestamp(year + 1, 1, 1))
            try:
                parts.append(fetch_day_ahead(zone, y0.strftime("%Y-%m-%d"), y1.strftime("%Y-%m-%d")))
            except RuntimeError as err:
                sys.exit(str(err))
            print(f"{zone} {year}: {len(parts[-1])} hours")
        prices = pd.concat(parts)
        prices = prices[~prices.index.duplicated()].sort_index().rename("price")
        original_index = prices.index
        prices, filled = fill_short_gaps(prices, max_hours=6)  # gaps longer than 6 hours stay missing
        filled_hours = prices.index[prices.notna() & ~prices.index.isin(original_index)]
        by_year = pd.Series(1, index=filled_hours).groupby(filled_hours.year).sum()
        print(f"{zone}: filled {filled} short-gap hours" + "".join(f" | {y}: {n}" for y, n in by_year.items()))
        prices = prices.dropna().rename_axis("utc_hour")
        prices.to_frame().to_parquet(out / f"prices_{zone}.parquet")


if __name__ == "__main__":
    main()
