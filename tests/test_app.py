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
