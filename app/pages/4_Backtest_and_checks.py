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
YIELD_RANGE = (1400, 1600)  # kWh/kWp per year, plausible for southern Italy
CI_BADGE = "https://github.com/OWNER/italian-renewables-rtm/actions"  # TODO Task 12: replace OWNER with the real GitHub owner once the remote exists

zone = common.DEFAULT_ZONE
case = common.get_example(zone)
common.header("Backtest and checks", case.is_synthetic)
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
energy = common.weather_year_energy(store.load_solar_puglia())
yield_kwh_kwp = float(energy.mean()) * 1000 / (case.capacity_mw * 1000)
ok = YIELD_RANGE[0] <= yield_kwh_kwp <= YIELD_RANGE[1]
st.markdown(
    f"{'✅' if ok else '❌'} Specific yield {yield_kwh_kwp:,.0f} kWh/kWp per year "
    f"(expected {YIELD_RANGE[0]:,}–{YIELD_RANGE[1]:,})."
)

st.subheader("Fair price range versus benchmarks")
st.markdown(f"Fair price range of this model: {rec.fair_low:.1f}–{rec.fair_mid:.1f} €/MWh.")
st.markdown(BENCHMARKS.read_text(encoding="utf-8"))

st.subheader("Continuous integration")
st.markdown(f"[![CI]({CI_BADGE}/workflows/ci.yml/badge.svg)]({CI_BADGE})")
st.caption(common.SOURCES)
