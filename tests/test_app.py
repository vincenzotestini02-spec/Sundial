"""Streamlit AppTest checks: every page runs on the default example and never crashes."""

import dataclasses

import shutil

import sys

from pathlib import Path



import pandas as pd

import pytest

import streamlit as st

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

    assert any("Prices for this zone are a synthetic placeholder" in t for t in texts)





HOME = str(ROOT / "app" / "Home.py")

ALL_PAGES = [HOME] + [str(ROOT / "app" / "pages" / p) for p in (

    "1_Asset_value.py", "2_Compare_offers.py", "3_Hedge.py", "4_Backtest_and_checks.py", "5_Report.py")]





@pytest.fixture

def data_copy(tmp_path, monkeypatch, fixture_data_dir):

    """A private copy of the fixture data dir that the app reads; caches are cleared before and after."""

    dest = tmp_path / "data"

    shutil.copytree(fixture_data_dir, dest)

    monkeypatch.setenv("SUNDIAL_DATA_DIR", str(dest))

    monkeypatch.delenv("SUNDIAL_FORCE_SYNTHETIC", raising=False)

    st.cache_resource.clear()

    yield dest

    st.cache_resource.clear()





@pytest.mark.parametrize("region,zone", [("Puglia", "SUD"), ("Sicilia", "SICI"), ("Lombardia", "NORD"),

                                         ("Sardegna", "SARD")])

def test_home_renders_for_region(region, zone, data_copy):

    at = AppTest.from_file(HOME, default_timeout=120)

    at.run()

    at.sidebar.selectbox(key="region").set_value(region).run()

    assert not at.exception

    assert any(zone in m.value or region in m.value for m in [*at.markdown, *at.caption])

    assert len(at.warning) == 0





@pytest.mark.parametrize("page", ALL_PAGES)

def test_every_page_uses_the_sidebar_region(page):

    at = AppTest.from_file(page, default_timeout=120).run()

    assert not at.exception and at.sidebar.selectbox(key="region").value == "Puglia"





def test_region_persists_across_pages(data_copy):

    at = AppTest.from_file(HOME, default_timeout=120)

    at.run()

    at.sidebar.selectbox(key="region").set_value("Sicilia").run()

    assert "SICI" in at.sidebar.caption[0].value





def test_zone_without_prices_falls_back_with_banner(data_copy):

    (data_copy / "prices_SARD.parquet").unlink()

    at = AppTest.from_file(HOME, default_timeout=120)

    at.run()

    at.sidebar.selectbox(key="region").set_value("Sardegna").run()

    assert not at.exception

    assert any("SYNTHETIC" in i.value for i in at.info) and len(at.warning) == 0





def test_footer_without_manifest(data_copy):

    (data_copy / "manifest.json").unlink()

    at = AppTest.from_file(HOME, default_timeout=120).run()

    assert not at.exception

    assert any(c.value == "Data source: unknown (no manifest)" for c in at.caption)





def test_footer_with_manifest(data_copy):

    at = AppTest.from_file(HOME, default_timeout=120).run()

    assert any(c.value.startswith("Data: ENTSO-E Transparency Platform (") for c in at.caption)





def test_status_notes_name_fallback_years_and_imbalance():

    from common import status_notes

    case = dataclasses.replace(load_example("SUD"), fallback_years=[2021, 2022], imbalance_source="placeholder")

    notes = status_notes(case)

    assert any("2021, 2022" in n for n in notes) and any("Imbalance" in n for n in notes)

    assert status_notes(dataclasses.replace(case, fallback_years=[], imbalance_source="computed")) == []





def test_asset_page_shows_zonal_solar_chart(data_copy):

    at = AppTest.from_file(str(ROOT / "app" / "pages" / "1_Asset_value.py"), default_timeout=120).run()

    assert not at.exception

    assert at.sidebar.number_input(key="lat").value == pytest.approx(41.46)

    assert any("Zonal solar production" in str(c.proto.spec) for c in at.get("plotly_chart"))





def test_asset_page_coordinates_follow_region(data_copy):

    at = AppTest.from_file(str(ROOT / "app" / "pages" / "1_Asset_value.py"), default_timeout=120).run()

    at.sidebar.selectbox(key="region").set_value("Lombardia").run()

    assert at.sidebar.number_input(key="lat").value == pytest.approx(45.16)





def test_hedge_shows_cap_note_and_slider_includes_floor(data_copy):

    at = AppTest.from_file(str(ROOT / "app" / "pages" / "3_Hedge.py"), default_timeout=120).run()

    assert not at.exception

    from common import get_recommendation

    rec = get_recommendation("SUD")

    if rec.floor_capped:

        assert any("not reachable" in i.value for i in at.info)

    if at.slider:

        assert at.slider[0].min <= rec.cvar_floor / 1e6 <= at.slider[0].max





def test_region_without_site_profile_shows_error_not_traceback(data_copy):

    (data_copy / "site_SARD.parquet").unlink()

    for page in ALL_PAGES:

        at = AppTest.from_file(page, default_timeout=120)

        at.run()

        at.sidebar.selectbox(key="region").set_value("Sardegna").run()

        assert not at.exception and any("not available yet" in e.value for e in at.error)

        at.sidebar.selectbox(key="region").set_value("Sicilia").run()

        assert not at.exception and len(at.error) == 0





def test_footer_flags_synthetic_prices(data_copy, monkeypatch):
    monkeypatch.setenv("SUNDIAL_FORCE_SYNTHETIC", "1")

    at = AppTest.from_file(HOME, default_timeout=120).run()

    assert any("synthetic placeholder" in c.value and c.value.startswith("Data:") for c in at.caption)

