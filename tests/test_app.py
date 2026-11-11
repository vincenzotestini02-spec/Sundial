"""Streamlit AppTest checks: every page runs on the default example and never crashes."""
import dataclasses
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ppa_italia.data.pvgis import PvgisError
from ppa_italia.example import load_example

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))  # so tests can import app/common.py
from common import offers_from_editor  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OFFER_ROW = dataclasses.asdict(load_example("SUD").offers[0])


@pytest.mark.parametrize("page", ["Home.py", "pages/1_Asset_value.py", "pages/2_Compare_offers.py"])
def test_page_runs_on_default_example(page):
    at = AppTest.from_file(str(ROOT / "app" / page), default_timeout=60).run()
    assert not at.exception
    assert any("Not trading advice" in m.value for m in at.caption)


def test_home_shows_headline():
    at = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=60).run()
    assert any(m.value.startswith(("Sign offer", "Stay merchant")) for m in at.markdown)


def test_synthetic_banner_is_info_not_warning():
    at = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=60).run()
    assert any("SYNTHETIC — placeholder until ENTSO-E data" in m.value for m in at.info)
    assert len(at.warning) == 0


def test_offers_from_editor_reports_bad_rows():
    df = pd.DataFrame([{**OFFER_ROW, "tenor_years": 0}])
    offers, errors = offers_from_editor(df)
    assert offers == [] and len(errors) == 1 and "tenor" in errors[0].lower()


def test_offers_from_editor_accepts_good_rows():
    offers, errors = offers_from_editor(pd.DataFrame([OFFER_ROW]))
    assert len(offers) == 1 and errors == []


def test_asset_page_falls_back_when_pvgis_fails(monkeypatch):
    monkeypatch.setattr("ppa_italia.data.pvgis.fetch_hourly_pv",
                        lambda *a, **k: (_ for _ in ()).throw(PvgisError("down")))
    at = AppTest.from_file(str(ROOT / "app" / "pages" / "1_Asset_value.py"), default_timeout=60).run()
    assert len(at.warning) == 0  # default site never calls PVGIS
    at.number_input(key="lat").set_value(45.0).run()  # non-default site -> PVGIS is called
    assert not at.exception and len(at.warning) >= 1


def test_offers_from_editor_rejects_empty_cells():
    df = pd.DataFrame([{**OFFER_ROW, "price": float("nan")}])
    offers, errors = offers_from_editor(df)
    assert offers == [] and errors == [f"Row 1 ({OFFER_ROW['name']}): price is empty"]


def test_win_share_bar_text_marks_fragile_winner():
    from common import win_share_bar_text
    assert win_share_bar_text(pd.Series([0.6, 0.4]), 0.70) == ["fragile", ""]
    assert win_share_bar_text(pd.Series([0.8, 0.2]), 0.70) == ["", ""]


@pytest.mark.parametrize("page", ["pages/3_Hedge.py", "pages/4_Backtest_and_checks.py", "pages/5_Report.py"])
def test_more_pages_run(page):
    at = AppTest.from_file(str(ROOT / "app" / page), default_timeout=60).run()
    assert not at.exception
    assert any("Not trading advice" in m.value for m in at.caption)


def test_hedge_infeasible_floor_shows_error():
    at = AppTest.from_file(str(ROOT / "app" / "pages" / "3_Hedge.py"), default_timeout=60).run()
    at.number_input(key="cvar_floor_override").set_value(1e12).run()
    assert any("No mix of these offers" in e.value for e in at.error)


def test_hedge_default_is_feasible():
    at = AppTest.from_file(str(ROOT / "app" / "pages" / "3_Hedge.py"), default_timeout=60).run()
    assert len(at.error) == 0


def test_home_uses_latest_price_year():
    from common import get_home_yearly
    prices_last = get_home_yearly("SUD").index.max()
    from ppa_italia.data import store
    assert prices_last == store.load_prices("SUD")[0].index.year.max()


def test_headline_labels_fair_range_as_pay_as_produced():
    from common import breakeven_line, headline
    from ppa_italia.recommend import Recommendation
    rec = Recommendation("C", 0.4, 80.0, 85.0, 67.0, 0.8, False, {"C": 0.4}, False, 0.0)
    assert "Fair pay-as-produced price range 80.0–85.0 €/MWh." in headline(rec)
    assert headline(rec).startswith("Sign offer C")
    assert "(floor level)" in breakeven_line(rec, "floor")
    assert "(floor level)" not in breakeven_line(rec, "pap")


def test_home_headline_on_page_says_pay_as_produced():
    at = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=60).run()
    assert any("pay-as-produced price range" in m.value for m in at.markdown)


def test_offers_from_editor_rejects_duplicate_names():
    df = pd.DataFrame([OFFER_ROW, OFFER_ROW])
    offers, errors = offers_from_editor(df)
    assert len(offers) == 1 and errors == [f"Row 2 ({OFFER_ROW['name']}): duplicate name"]


@pytest.mark.parametrize("page", ["Home.py", "pages/5_Report.py"])
def test_term_sheet_expanders(page):
    at = AppTest.from_file(str(ROOT / "app" / page), default_timeout=60).run()
    labels = [e.label for e in at.expander]
    assert "Term sheet (EN)" in labels and "Term sheet (IT)" in labels


def test_criteria_for_display_uses_meur_and_labels():
    from common import criteria_for_display
    table = pd.DataFrame({"npv_mean": [2.5e6], "npv_p10": [1e6], "credit_el": [500.0], "tenor_years": [10],
                          "indexation_pct": [0.02], "imbalance_on_buyer": [1], "penalty_severity": [3]},
                         index=["A"])
    out = criteria_for_display(table)
    assert out.loc["A", "Mean NPV (M€)"] == pytest.approx(2.5)
    assert out.loc["A", "Indexation (%/yr)"] == pytest.approx(2.0)
    assert out.loc["A", "Imbalance on buyer"] == "yes"


def test_asset_page_hides_wind_without_profile_and_no_dev_instructions():
    at = AppTest.from_file(str(ROOT / "app" / "pages" / "1_Asset_value.py"), default_timeout=60).run()
    assert not at.exception
    assert at.radio[0].options == ["Solar"]
    texts = [m.value for m in at.caption] + [m.value for m in at.info]
    assert not any("scripts/" in t for t in texts)
    assert any("share the same synthetic price series" in t for t in texts)
