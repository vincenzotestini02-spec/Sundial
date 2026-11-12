import io
import zipfile

import pandas as pd
import pytest

from ppa_italia.data.file_library import IT_AREA_CODES, read_generation, read_generation_zones, read_imbalance, read_prices

HEADER_P = "InstanceCode\tDateTime(UTC)\tResolutionCode\tAreaCode\tAreaDisplayName\tAreaTypeCode\tAreaMapCode\tContractType\tSequence\tPrice[Currency/MWh]\tCurrency\tUpdateTime(UTC)\n"
HEADER_G = "DateTime(UTC)\tResolutionCode\tAreaCode\tAreaDisplayName\tAreaTypeCode\tAreaMapCode\tProductionType\tActualGenerationOutput[MW]\tActualConsumption[MW]\tUpdateTime(UTC)\n"
SUD = IT_AREA_CODES["SUD"]


def _zip(tmp_path, name, files):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w") as z:
        for fname, text in files.items():
            z.writestr(fname, text)
    return p


def _price_row(ts, res, area, price, contract="Day-ahead"):
    return f"x\t{ts}\t{res}\t{area}\tA\tBZN\tM\t{contract}\t\t{price}\tEUR\t2026-01-01 00:00:00\n"


def test_read_prices_filters_zone_contract_and_averages_quarter_hours(tmp_path):
    text = HEADER_P
    text += _price_row("2025-10-01 00:00:00", "PT15M", SUD, 10)
    text += _price_row("2025-10-01 00:15:00", "PT15M", SUD, 20)
    text += _price_row("2025-10-01 00:30:00", "PT15M", SUD, 30)
    text += _price_row("2025-10-01 00:45:00", "PT15M", SUD, 40)
    text += _price_row("2025-10-01 00:00:00", "PT15M", "OTHER", 999)
    text += _price_row("2025-10-01 00:00:00", "PT15M", SUD, 555, contract="Intraday")
    z = _zip(tmp_path, "p.zip", {"2025_10_EnergyPrices_12.1.D_r3.1.csv": text})
    out = read_prices([z], zones=["SUD"])
    s = out["SUD"]
    assert list(s.values) == [25.0]
    assert s.index[0] == pd.Timestamp("2025-10-01 00:00", tz="UTC")


def test_read_prices_skips_months_before_start_and_merges_zips(tmp_path):
    old = _zip(tmp_path, "a.zip", {
        "2019_01_EnergyPrices_12.1.D_r3.1.csv": HEADER_P + _price_row("2019-01-01 00:00:00", "PT60M", SUD, 1),
        "2021_01_EnergyPrices_12.1.D_r3.1.csv": HEADER_P + _price_row("2021-01-01 00:00:00", "PT60M", SUD, 50),
    })
    new = _zip(tmp_path, "b.zip", {
        "2021_02_EnergyPrices_12.1.D_r3.1.csv": HEADER_P + _price_row("2021-02-01 00:00:00", "PT60M", SUD, 60),
    })
    s = read_prices([old, new], zones=["SUD"], start_month="2021_01")["SUD"]
    assert list(s.values) == [50.0, 60.0]


def test_read_prices_rejects_unknown_zone(tmp_path):
    z = _zip(tmp_path, "p.zip", {"2021_01_EnergyPrices_12.1.D_r3.1.csv": HEADER_P})
    with pytest.raises(KeyError):
        read_prices([z], zones=["ATLANTIS"])


def test_read_generation_keeps_solar_of_zone_hourly(tmp_path):
    rows = HEADER_G
    rows += f"2023-06-01 10:00:00\tPT15M\t{SUD}\tS\tBZN\tM\tSolar\t100\t\tu\n"
    rows += f"2023-06-01 10:15:00\tPT15M\t{SUD}\tS\tBZN\tM\tSolar\t300\t\tu\n"
    rows += f"2023-06-01 10:00:00\tPT15M\t{SUD}\tS\tBZN\tM\tWind Onshore\t999\t\tu\n"
    rows += f"2023-06-01 10:00:00\tPT15M\tOTHER\tS\tBZN\tM\tSolar\t999\t\tu\n"
    z = _zip(tmp_path, "g.zip", {"2023_06_AggregatedGenerationPerType_16.1.B_C_r3.csv": rows})
    s = read_generation([z], zone="SUD", production_type="Solar")
    assert list(s.values) == [200.0]
    assert s.index[0] == pd.Timestamp("2023-06-01 10:00", tz="UTC")


HEADER_I = ("DateTime(UTC)\tResolutionCode\tAreaCode\tAreaDisplayName\tAreaTypeCode\tAreaMapCode\t"
            "PositiveImbalancePrice[Currency/MWh]\tPositiveScarcity[Currency/MWh]\tPositiveIncentive[Currency/MWh]\t"
            "PositiveFinancialNeutrality[Currency/MWh] \tNegativeImbalancePrice[Currency/MWh]\tNegativeScarcity[Currency/MWh]\t"
            "NegativeIncentive[Currency/MWh]\tNegativeFinancialNeutrality[Currency/MWh]\tCurrency\tStatus\tUpdateTime(UTC)\n")


def imbalance_row(ts, area, pos, neg):
    return f"{ts}\tPT15M\t{area}\tIT-South\tSCA\tM\t{pos}\t0\t0\t0\t{neg}\t0\t0\t0\tEUR\tFinal\tu\n"


def zip_with_rows(tmp_path):
    rows = HEADER_I
    for ts, pos, neg in [("00:00", 80, 0), ("00:15", 0, 60), ("00:30", 70, 90), ("00:45", 0, 0)]:
        rows += imbalance_row(f"2026-01-01 {ts}:00", SUD, pos, neg)
    rows += imbalance_row("2026-01-01 00:00:00", "OTHER", 999, 0)
    return _zip(tmp_path, "i.zip", {"2026_01_ImbalancePrices_17.1.G_r3.1.csv": rows})


def test_read_imbalance_takes_non_zero_side(tmp_path):
    s = read_imbalance([zip_with_rows(tmp_path)], zones=["SUD"], start_month="2026_01")["SUD"]
    assert s.iloc[0] == pytest.approx((80 + 60 + 80) / 3)  # (70+90)/2=80; the (0,0) row is dropped
    assert len(s) == 1


def test_read_generation_zones_reads_many_zones(tmp_path):
    cn = IT_AREA_CODES["CNOR"]
    rows = HEADER_G
    rows += f"2023-06-01 10:00:00\tPT60M\t{SUD}\tS\tBZN\tM\tSolar\t100\t\tu\n"
    rows += f"2023-06-01 10:00:00\tPT60M\t{cn}\tS\tBZN\tM\tSolar\t40\t\tu\n"
    z = _zip(tmp_path, "g.zip", {"2023_06_AggregatedGenerationPerType_16.1.B_C_r3.csv": rows})
    out = read_generation_zones([z], zones=["SUD", "CNOR"])
    assert out["SUD"].iloc[0] == 100.0 and out["CNOR"].iloc[0] == 40.0
