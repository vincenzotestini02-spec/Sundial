"""Asset value: capture price vs baseload, capture rate, negative-price hours, P50/P90."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.data import pvgis, store  # noqa: E402
from ppa_italia.pricing import p_levels  # noqa: E402
from ppa_italia.value import yearly_summary  # noqa: E402
from ppa_italia.zones import ZONE_SITE  # noqa: E402

st.set_page_config(page_title="Asset value", layout="wide")

PARTIAL_YEAR_HOURS = 8700  # fewer hours than this marks a partial year


@st.cache_data(ttl=86400)
def fetch_pv(lat: float, lon: float, peak_kw: float) -> pd.Series:
    """Hourly PVGIS production (MWh) for 2005-2023, cached for a day."""
    series, _ = pvgis.fetch_hourly_pv(lat, lon, peak_kw, 2005, 2023)
    return series


def wind_available(zone: str) -> bool:
    """True when a wind capacity-factor profile has been built for the zone."""
    try:
        store.load_wind_cf(zone)
    except FileNotFoundError:
        return False
    return True


def solar_profile(zone: str, lat: float, lon: float, mw: float) -> pd.Series:
    """PVGIS profile for a custom site; the zone's site profile (scaled) at the default site or on failure."""
    site, site_lat, site_lon = ZONE_SITE[zone]
    if (lat, lon) != (site_lat, site_lon):
        try:
            with st.spinner("Fetching the PVGIS solar profile for this site..."):
                return fetch_pv(lat, lon, mw * 1000)
        except pvgis.PvgisError as err:
            st.warning(f"PVGIS unavailable ({err}); using the {site} profile scaled to {mw:g} MW.")
    return store.load_site_profile(zone) * mw


def zonal_solar_figure(prices: pd.Series, zone_solar: pd.Series) -> go.Figure:
    """Yearly zonal solar production (TWh, bars) and its capture rate (%, line); partial years are flagged."""
    s = yearly_summary(prices, zone_solar)
    labels = [f"{int(y)} (partial)" if h < PARTIAL_YEAR_HOURS else str(int(y)) for y, h in zip(s.index, s["hours"])]
    opacity = [0.45 if h < PARTIAL_YEAR_HOURS else 1.0 for h in s["hours"]]
    fig = go.Figure()
    fig.add_bar(x=labels, y=s["gen_mwh"] / 1e6, name="Solar production (TWh)", marker_opacity=opacity)
    fig.add_scatter(x=labels, y=s["capture_rate"] * 100, name="Solar capture rate (%)", yaxis="y2", mode="lines+markers")
    fig.update_layout(
        title="Zonal solar production (TWh) and solar capture rate (%)",
        yaxis=dict(title="TWh"), yaxis2=dict(title="% of baseload", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )
    return fig


zone = common.region_selector()
site_name, site_lat, site_lon = ZONE_SITE[zone]
EXAMPLE_MW = 20.0
with st.sidebar:
    has_wind = wind_available(zone)
    tech = st.radio("Technology", ["Solar", "Wind"] if has_wind else ["Solar"])
    if not has_wind:
        st.caption("Wind is not available for this zone yet: its profile needs real ENTSO-E data.")
    mw = st.number_input("Capacity (MW)", min_value=0.1, value=EXAMPLE_MW, step=1.0, key="mw")
    if st.session_state.get("_site_zone") != zone:  # new region: reset the coordinates to its zone site
        st.session_state["lat"], st.session_state["lon"] = site_lat, site_lon
        st.session_state["_site_zone"] = zone
    lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, format="%.2f", key="lat")
    lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, format="%.2f", key="lon")

case = common.get_example(zone)
prices, is_synthetic = store.load_prices(zone)
common.header("Asset value", case)
st.caption(common.TYPICAL_YEAR_NOTE)
st.caption(f"Solar site: {site_name} ({site_lat:.2f}, {site_lon:.2f}), representative of zone {zone}. "
           "Change latitude/longitude in the sidebar to fetch another site from PVGIS.")
if is_synthetic:
    st.caption("All zones share the same synthetic price series, so switching zone does not change the results yet.")

gen = solar_profile(zone, lat, lon, mw) if tech == "Solar" else store.load_wind_cf(zone) * mw

weather_energy = common.weather_year_energy(gen)  # P50/P90 come from the real weather years
if tech == "Solar":
    gen = common.align_to_prices(gen, prices)  # typical weather year on every price year
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

fig = go.Figure(go.Bar(x=years, y=summary["gen_share_in_zero_or_negative_hours"] * 100))
fig.update_layout(title="Share of output in hours at or below zero (%)", yaxis_title="% of annual output")
right.plotly_chart(fig, width="stretch")

levels = p_levels(weather_energy if len(weather_energy) else summary["gen_mwh"])
fig = go.Figure(go.Bar(x=["P90", "P50"], y=[levels["P90"], levels["P50"]]))
fig.update_layout(title="Annual production (MWh)", yaxis_title="MWh/yr")
left.plotly_chart(fig, width="stretch")

zone_solar = store.load_zone_solar(zone)
if zone_solar is None:
    st.info(f"No zonal solar production data for {zone}: the zonal chart is not available.")
else:
    try:
        right.plotly_chart(zonal_solar_figure(prices, zone_solar), width="stretch")
        right.caption("Zonal solar: ENTSO-E Transparency Platform. Faded bars are partial years.")
    except ValueError as err:
        st.info(f"Prices and zonal solar do not overlap in time ({err}).")

st.caption(common.SOURCES)
common.footer()
if is_synthetic:
    st.caption(f"Prices shown: {common.SYNTHETIC_LABEL}")
