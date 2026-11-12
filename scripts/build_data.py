"""Build the precomputed data files (prices, zone solar, imbalance, PVGIS site profiles).

File Library:  python scripts/build_data.py --source file-library --prices-zips a.zip b.zip
                   --solar-zips g.zip --imbalance-zips i.zip --zones SUD NORD --start 2021-01
API:           ENTSOE_TOKEN=... python scripts/build_data.py --source api --zones SUD --start 2021-01
Add --sites to also fetch the PVGIS site profiles (no key needed). Output goes to the data dir
(SUNDIAL_DATA_DIR, default data/precomputed). Both sources write identical files.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ppa_italia.data.build import build_from_api, build_from_file_library, write_site_profiles
from ppa_italia.data.entsoe import make_client
from ppa_italia.data.store import data_dir
from ppa_italia.zones import ZONES


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["file-library", "api"], required=True)
    ap.add_argument("--prices-zips", nargs="*", default=[], type=Path)
    ap.add_argument("--solar-zips", nargs="*", default=[], type=Path)
    ap.add_argument("--imbalance-zips", nargs="*", default=[], type=Path)
    ap.add_argument("--zones", nargs="*", default=list(ZONES))
    ap.add_argument("--start", default="2021-01", help="YYYY-MM")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD, API only (default today)")
    ap.add_argument("--sites", action="store_true", help="also build PVGIS site profiles")
    args = ap.parse_args()

    out = data_dir()
    if args.source == "file-library":
        manifest = build_from_file_library(args.prices_zips, args.solar_zips, args.imbalance_zips,
                                           args.zones, args.start.replace("-", "_"), out)
    else:
        manifest = build_from_api(make_client(), args.zones, f"{args.start}-01",
                                  args.end or date.today().isoformat(), out)
    for name, info in sorted(manifest["files"].items()):
        print(f"{name}: {info['rows']} rows, {info['first']} .. {info['last']}, "
              f"{info.get('filled_hours', 0)} hours gap-filled")
    if args.sites:
        write_site_profiles(out)
        print("site profiles written")


if __name__ == "__main__":
    main()
