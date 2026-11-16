"""Home: what Sundial does and how it works, in sections. The worked example lives on the other pages."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))  # make app/common.py importable

import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.data import store  # noqa: E402
from ppa_italia.zones import REGION_TO_ZONE  # noqa: E402

st.set_page_config(page_title="Sundial", page_icon=":material/wb_sunny:", layout="wide")

METHODOLOGY_URL = "https://github.com/vincenzotestini02-spec/Sundial/blob/main/docs/methodology.md"

FEATURES = [
    (":material/solar_power:", "Value the asset",
     "Capture price against baseload, capture rate, hours at or below zero and P50/P90 production, "
     "for any site in Italy through PVGIS."),
    (":material/compare_arrows:", "Compare PPA offers",
     "Pay-as-produced, baseload and floor structures, buyer credit risk, multi-criteria tender scoring "
     "and a robustness test on the weights."),
    (":material/shield:", "Size the hedge",
     "How much production to put under contract, with a CVaR floor on the worst 10% of price scenarios "
     "and the full risk and return frontier."),
    (":material/description:", "Price and report",
     "A fair pay-as-produced price range, the merchant break-even and a two-page customer PDF "
     "in Italian or English."),
]

STEPS = [
    ("Scenarios", "Real ENTSO-E prices and zonal solar shape, PVGIS weather years, three price levels."),
    ("Offers", "Each offer gets an expected revenue, a P10 downside revenue and an expected credit loss."),
    ("Choice", "Tender scoring picks the winner; thousands of random weightings test how often it still wins."),
    ("Size and price", "A linear program sizes the hedge under the CVaR floor; the fair price follows from "
                       "capture price, imbalance, margin and GoO value."),
]

PAGES = [
    ("pages/1_Asset_value.py", "Asset value", ":material/solar_power:", "Capture price, capture rate, P50/P90"),
    ("pages/2_Compare_offers.py", "Compare offers", ":material/compare_arrows:", "Edit offers, weights, robustness"),
    ("pages/3_Hedge.py", "Hedge", ":material/shield:", "How much to sign, CVaR floor"),
    ("pages/4_Backtest_and_checks.py", "Checks", ":material/fact_check:", "Backtest, yield, benchmarks"),
    ("pages/5_Report.py", "Report", ":material/download:", "Customer PDF and term sheet"),
]

zone = common.region_selector()
case = common.load_case_or_stop(zone)
common.header("Sundial", case)
st.markdown(
    "#### Route-to-market and PPA valuation for Italian renewables\n"
    "Sundial takes a renewable asset anywhere in Italy and a set of power purchase agreement offers, and turns "
    "them into one recommendation: which offer to sign, for how much of the production, and at what price."
)

st.write("")
st.subheader("What Sundial does", anchor=False)
for col, (icon, title, text) in zip(st.columns(len(FEATURES)), FEATURES):
    with col.container(border=True, height="stretch"):
        st.markdown(f"{icon} **{title}**")
        st.caption(text)

st.write("")
st.subheader("How it works", anchor=False)
for col, (n, (title, text)) in zip(st.columns(len(STEPS)), enumerate(STEPS, start=1)):
    col.markdown(f"**{n}. {title}**")
    col.caption(text)
st.caption(f"Every step feeds the next, so the pages, the report and the term sheet agree. "
           f"[Models and their limits]({METHODOLOGY_URL})")

st.write("")
st.subheader("Explore the app", anchor=False)
st.caption("Choose the asset's region in the sidebar: every page re-runs for its bidding zone.")
for col, (path, label, icon, blurb) in zip(st.columns(len(PAGES)), PAGES):
    with col.container(border=True, height="stretch"):
        st.page_link(path, label=f"**{label}**", icon=icon)
        st.caption(blurb)

st.write("")
st.subheader("Data", anchor=False)
prices, _ = store.load_prices(zone)
c1, c2, c3 = st.columns(3)
c1.metric("Regions", len(REGION_TO_ZONE))
c2.metric("Bidding zones", len(set(REGION_TO_ZONE.values())))
c3.metric("Price history", f"{prices.index.year.min()} to {prices.index.year.max()}")
st.caption("Day-ahead prices, imbalance prices and zonal solar generation from the ENTSO-E Transparency Platform; "
           "site solar profiles from PVGIS (European Commission, JRC). Offers and buyers are illustrative assumptions.")

st.divider()
st.caption(common.SOURCES)
common.footer(zone, case.is_synthetic)
