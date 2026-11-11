"""Home: the customer's question, the one-sentence recommendation and key numbers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))  # make app/common.py importable

import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.pricing import p_levels  # noqa: E402

st.set_page_config(page_title="PPA Italia", layout="wide")

zone = common.DEFAULT_ZONE
case = common.get_example(zone)
common.header("PPA Italia: value an Italian renewable PPA", case.is_synthetic)

st.subheader("The customer's question")
st.write(
    "A 20 MW solar park in Puglia (zone SUD) has received several PPA offers. "
    "Which one should it sign, for how much of its production, and what is a fair price?"
)

try:
    rec = common.get_recommendation(zone)
    yearly = common.get_home_yearly(zone)
except Exception as err:  # never crash on the landing page
    st.error(f"The example could not be computed: {err}")
    st.stop()

st.markdown(common.headline(rec))
be = "n/a" if rec.breakeven != rec.breakeven else f"{rec.breakeven:.1f} €/MWh"
st.markdown(f"Merchant break-even price of offer {rec.offer}: {be}")
if rec.fragile:
    st.markdown("The winner is fragile: it wins in fewer than 70% of weightings.")

full = yearly[yearly["hours"] >= 8700]
used = full if not full.empty else yearly
latest = used.iloc[-1]
p50 = p_levels(used["gen_mwh"])["P50"]
c1, c2, c3 = st.columns(3)
c1.metric(f"Capture rate {int(latest.name)}", f"{latest['capture_rate'] * 100:.0f}%")
c2.metric("P50 production", f"{p50:,.0f} MWh/yr")
c3.metric("Win share of best offer", f"{rec.win_share * 100:.0f}%")

st.subheader("Explore")
st.page_link("pages/1_Asset_value.py", label="Asset value: capture price, capture rate, P50/P90")
st.page_link("pages/2_Compare_offers.py", label="Compare offers: edit offers, weights and robustness")
st.markdown("Term sheet (EN/IT) — in docs/")
st.caption(common.SOURCES)
