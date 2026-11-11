"""Asset value: capture price vs baseload, capture rate, negative-price hours, P50/P90."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.data import pvgis, store  # noqa: E402
from ppa_italia.data.entsoe import ZONES  # noqa: E402
from ppa_italia.pricing import p_levels  # noqa: E402
from ppa_italia.value import yearly_summary  # noqa: E402

st.set_page_config(page_title="Asset value", layout="wide")

PUGLIA = (41.46, 15.55)
EXAMPLE_MW = 20.0


@st.cache_data(ttl=86400)
def fetch_pv(lat: float, lon: float, peak_kw: float) -> pd.Series:
    """Hourly PVGIS production (MWh) for 2005-2023, cached for a day."""
    series, _ = pvgis.fetch_hourly_pv(lat, lon, peak_kw, 2005, 2023)
    return series


def solar_profile(lat: float, lon: float, mw: float) -> pd.Series:
    """PVGIS profile for a custom site; the Puglia profile (scaled) at the default site or on failure."""
    if (lat, lon) != PUGLIA:
        try:
            return fetch_pv(lat, lon, mw * 1000)
        except pvgis.PvgisError as err:
            st.warning(f"PVGIS unavailable ({err}); using the Puglia profile scaled to {mw:g} MW.")
    return store.load_solar_puglia() * (mw / EXAMPLE_MW)


with st.sidebar:
    zone = st.selectbox("Bidding zone", list(ZONES), index=list(ZONES).index(common.DEFAULT_ZONE))
    tech = st.radio("Technology", ["Solar", "Wind"])
    mw = st.number_input("Capacity (MW)", min_value=0.1, value=EXAMPLE_MW, step=1.0, key="mw")
    lat = st.number_input("Latitude", value=PUGLIA[0], format="%.2f", key="lat")
    lon = st.number_input("Longitude", value=PUGLIA[1], format="%.2f", key="lon")

prices, is_synthetic = store.load_prices(zone)
common.header("Asset value", is_synthetic)

if tech == "Solar":
    gen = solar_profile(lat, lon, mw)
else:
    try:
        gen = store.load_wind_cf(zone) * mw
    except FileNotFoundError:
        st.info("Wind profile not built yet (run scripts/build_wind_proxy.py). Choose Solar to continue.")
        st.stop()

try:
    summary = yearly_summary(prices, gen)
except ValueError as err:
    st.info(f"Prices and production do not overlap in time, so no value can be computed ({err}).")
    st.stop()

years = summary.index.astype(int)
left, right = st.columns(2)

fig = go.Figure()
fig.add_bar(x=years, y=summary["baseload_eur_mwh"], name="Baseload price")
fig.add_bar(x=years, y=summary["capture_eur_mwh"], name="Capture price")
fig.update_layout(barmode="group", title="Capture price vs baseload (€/MWh)", yaxis_title="€/MWh")
left.plotly_chart(fig, width="stretch")

fig = go.Figure(go.Scatter(x=years, y=summary["capture_rate"] * 100, mode="lines+markers"))
fig.update_layout(title="Capture rate (%)", yaxis_title="% of baseload")
right.plotly_chart(fig, width="stretch")

fig = go.Figure(go.Bar(x=years, y=summary["zero_or_negative_hours"]))
fig.update_layout(title="Hours with price at or below zero", yaxis_title="hours")
left.plotly_chart(fig, width="stretch")

full = summary[summary["hours"] >= 8700]
levels = p_levels((full if not full.empty else summary)["gen_mwh"])
fig = go.Figure(go.Bar(x=["P90", "P50"], y=[levels["P90"], levels["P50"]]))
fig.update_layout(title="Annual production (MWh)", yaxis_title="MWh/yr")
right.plotly_chart(fig, width="stretch")

st.caption(common.SOURCES)
if is_synthetic:
    st.caption(f"Prices shown: {common.SYNTHETIC_LABEL}")
