import json
import zipfile

import pandas as pd
import pytest

from ppa_italia.data.build import build_from_api, build_from_file_library, write_zone_files
from ppa_italia.data.file_library import IT_AREA_CODES
from tests.test_file_library import HEADER_G, HEADER_I, HEADER_P, imbalance_row

SUD = IT_AREA_CODES["SUD"]
DAYS = pd.date_range("2026-01-01", periods=48 * 4, freq="15min", tz="UTC")  # 2 days, quarter-hours


def _price(i):
    return 50.0 + i % 7


def _solar(i):
    return float(i % 11) * 10


def _imb(i):
    """(positive, negative) for quarter-hour i: alternating sides, some both, some neither."""
    return [(80.0, 0.0), (0.0, 60.0), (70.0, 90.0), (0.0, 0.0)][i % 4]


def make_equivalent_zips(tmp_path):
    p, g, im = HEADER_P, HEADER_G, HEADER_I
    for i, ts in enumerate(DAYS):
        t = ts.strftime("%Y-%m-%d %H:%M:%S")
        p += f"x\t{t}\tPT15M\t{SUD}\tA\tBZN\tM\tDay-ahead\t\t{_price(i)}\tEUR\tu\n"
        g += f"{t}\tPT15M\t{SUD}\tS\tBZN\tM\tSolar\t{_solar(i)}\t\tu\n"
        im += imbalance_row(t, SUD, *_imb(i))
    out = {}
    for key, name, text in [("prices", "2026_01_EnergyPrices_12.1.D_r3.1.csv", p),
                            ("solar", "2026_01_AggregatedGenerationPerType_16.1.B_C_r3.csv", g),
                            ("imbalance", "2026_01_ImbalancePrices_17.1.G_r3.1.csv", im)]:
        path = tmp_path / f"{key}.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr(name, text)
        out[key] = [path]
    return out


class StubClient:
    """Mimics EntsoePandasClient: tz-aware Europe/Rome frames shaped like entsoe-py's."""

    def __init__(self):
        idx = DAYS.tz_convert("Europe/Rome")
        self.prices = pd.Series([_price(i) for i in range(len(idx))], index=idx)
        self.solar = pd.DataFrame({"Solar": [_solar(i) for i in range(len(idx))]}, index=idx)
        self.imb = pd.DataFrame({"Long": [_imb(i)[0] for i in range(len(idx))],
                                 "Short": [_imb(i)[1] for i in range(len(idx))]}, index=idx)

    def query_day_ahead_prices(self, country_code, start, end, resolution=None):
        return self.prices

    def query_generation(self, country_code, start, end, psr_type=None, nett=False, **kwargs):
        assert psr_type == "B16"
        return self.solar

    def query_imbalance_prices(self, country_code, start, end, psr_type=None):
        return self.imb


def test_both_sources_write_identical_files(tmp_path):
    zips = make_equivalent_zips(tmp_path)
    a = build_from_file_library(zips["prices"], zips["solar"], zips["imbalance"], ["SUD"], "2026_01", tmp_path / "fl")
    b = build_from_api(StubClient(), ["SUD"], "2026-01-01", "2026-01-03", tmp_path / "api")
    for name in ["prices_SUD.parquet", "solar_zone_SUD.parquet", "imbalance_SUD.parquet"]:
        pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "fl" / name), pd.read_parquet(tmp_path / "api" / name))
    assert a["source"] == "file-library" and b["source"] == "api"


def test_manifest_records_range_and_rows(tmp_path):
    idx = pd.date_range("2026-01-01", periods=5, freq="h", tz="UTC")
    s = pd.Series(range(5), index=idx, dtype=float)
    m = write_zone_files({"SUD": s}, {"SUD": s}, {"SUD": s}, tmp_path, "api")
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk["files"] == m["files"]
    entry = m["files"]["prices_SUD.parquet"]
    assert entry == {"first": idx[0].isoformat(), "last": idx[-1].isoformat(), "rows": 5}
    assert m["source"] == "api" and "built_utc" in m


def test_write_zone_files_fills_short_gaps(tmp_path):
    idx = pd.DatetimeIndex(pd.to_datetime(["2026-01-01 00:00", "2026-01-01 03:00"], utc=True))
    m = write_zone_files({"SUD": pd.Series([10.0, 40.0], index=idx)}, {}, {}, tmp_path, "api")
    assert m["files"]["prices_SUD.parquet"]["rows"] == 4
    assert list(pd.read_parquet(tmp_path / "prices_SUD.parquet")["price"]) == [10.0, 20.0, 30.0, 40.0]
