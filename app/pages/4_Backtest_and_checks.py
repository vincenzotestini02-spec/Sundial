"""Backtest and checks: forecast error, specific-yield sanity check and published benchmarks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.data import store  # noqa: E402
from ppa_italia.pricing import backtest_trailing_capture  # noqa: E402

st.set_page_config(page_title="Backtest and checks", layout="wide")

BENCHMARKS = Path(__file__).resolve().parents[2] / "docs" / "benchmarks.md"
YIELD_RANGE = (1100, 1800)  # kWh/kWp per year, plausible for Italy
CI_BADGE = "https://github.com/vincenzotestini02-spec/Sundial/actions"

zone = common.region_selector()
case = common.load_case_or_stop(zone)
common.header("Backtest and checks", case)
st.caption(common.TYPICAL_YEAR_NOTE)

rec = common.get_recommendation(zone)
prices, _ = store.load_prices(zone)
gen = common.get_aligned_solar(zone)

st.subheader("Backtest: last year's capture price as next year's forecast")
try:
    bt = backtest_trailing_capture(prices, gen)
    st.dataframe(bt.round(1), width="stretch")
    st.metric("Mean absolute error", f"{bt['error_eur_mwh'].abs().mean():.1f} €/MWh")
except ValueError as err:
    st.info(f"Not enough years of prices for a backtest ({err}).")

st.subheader("Specific yield check")
energy = common.weather_year_energy(store.load_site_profile(zone) * case.capacity_mw)
yield_kwh_kwp = float(energy.mean()) * 1000 / (case.capacity_mw * 1000)
ok = YIELD_RANGE[0] <= yield_kwh_kwp <= YIELD_RANGE[1]
st.markdown(
    f"{'✅' if ok else '❌'} Specific yield {yield_kwh_kwp:,.0f} kWh/kWp per year "
    f"(expected {YIELD_RANGE[0]:,}–{YIELD_RANGE[1]:,})."
)

st.subheader("Fair pay-as-produced price range versus benchmarks")
st.markdown(f"Fair pay-as-produced price range of this model: {rec.fair_low:.1f}–{rec.fair_mid:.1f} €/MWh.")
prefix = "The synthetic fair range" if case.is_synthetic else "The fair range"
st.caption(f"{prefix} is not comparable with the LevelTen figure below: different "
           "price data, contract structure and percentile.")
note = common.static_doc_caption(zone, "benchmarks block")
if note:
    st.caption(note)
st.markdown(BENCHMARKS.read_text(encoding="utf-8"))

st.subheader(f"Assumptions for zone {zone}")
for line in common.assumption_lines(case, rec):
    st.markdown(f"- {line}")

st.subheader("Continuous integration")
st.markdown(f"[![CI]({CI_BADGE}/workflows/ci.yml/badge.svg)]({CI_BADGE})")
st.caption(common.SOURCES)
common.footer(zone, case.is_synthetic)
