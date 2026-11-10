"""Build the hourly profile of the fictional 20 MW Puglia solar park from PVGIS.

Site: Tavoliere plain near Foggia (41.46 N, 15.55 E), SUD bidding zone.
Output:
  data/processed/puglia_solar_hourly.csv  (UTC hour, MWh)
  data/processed/puglia_solar_yearly.csv  (yield per weather year, P50/P90)

Outside check: the specific yield should sit in the range of published PVGIS/Puglia
fixed-tilt yields (~1,400-1,600 kWh/kWp); the script prints it next to that range.
Source: PVGIS (c) European Union, 2001-2026.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.value_engine.pvgis import fetch_hourly_pv  # noqa: E402

LAT, LON, PEAK_KW = 41.46, 15.55, 20_000
START, END = 2005, 2023  # full PVGIS-SARAH3 range at time of writing


def main() -> None:
    out = ROOT / "data" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    gen, inputs = fetch_hourly_pv(LAT, LON, PEAK_KW, START, END)
    gen.to_csv(out / "puglia_solar_hourly.csv", index_label="utc_hour")

    yearly = gen.groupby(gen.index.year).sum().rename("gen_mwh").to_frame()
    yearly["specific_yield_kwh_kwp"] = yearly["gen_mwh"] * 1000 / PEAK_KW
    yearly.to_csv(out / "puglia_solar_yearly.csv", index_label="weather_year")

    y = yearly["gen_mwh"]
    tilt = inputs["mounting_system"]["fixed"]
    print(f"Mounting: slope {tilt['slope']['value']} deg, azimuth {tilt['azimuth']['value']} deg (PVGIS optimal)")
    print(f"Weather years {START}-{END}: n={len(y)}")
    print(f"P50 production: {np.percentile(y, 50):,.0f} MWh/yr | P90: {np.percentile(y, 10):,.0f} MWh/yr")
    print(f"Specific yield mean: {yearly['specific_yield_kwh_kwp'].mean():,.0f} kWh/kWp (expected ~1,400-1,600)")
    print(f"Inter-annual variability (std/mean): {y.std() / y.mean():.1%}")


if __name__ == "__main__":
    main()
