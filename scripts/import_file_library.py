"""Build the app's price files from ENTSO-E File Library zips (no API token needed).

Usage:
    python scripts/import_file_library.py data/raw/energyprices.zip data/raw/Energyprices2.zip

Writes data/precomputed/prices_{ZONE}.parquet for NORD, SUD and SICI from January 2021
and prints the hours per zone and the short gaps filled. Source: ENTSO-E Transparency Platform.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ppa_italia.data.file_library import build_from_zips
from ppa_italia.data.store import PRECOMPUTED

ZONES = ["NORD", "SUD", "SICI"]


def main(paths: list[str]) -> None:
    if not paths:
        sys.exit(__doc__)
    report = build_from_zips([Path(p) for p in paths], PRECOMPUTED, ZONES)
    for zone, (hours, filled) in report.items():
        print(f"{zone}: {hours} hours written, {filled} short-gap hours filled")


if __name__ == "__main__":
    main(sys.argv[1:])
