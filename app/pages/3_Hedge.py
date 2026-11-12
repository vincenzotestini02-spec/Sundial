"""Hedge: how much of the production to sign, under a floor on the worst-10% outcome (CVaR)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.hedge import cvar, max_cvar, optimise_allocation  # noqa: E402

st.set_page_config(page_title="Hedge", layout="wide")

MEUR = 1e6
INFEASIBLE_MSG = (
    "No mix of these offers keeps the worst 10% of outcomes above this floor. "
    "Lower the floor or add an offer with a higher guaranteed price."
)

zone = common.region_selector()
case = common.load_case_or_stop(zone)
common.header("Hedge", case)
st.write(
    "Choose how bad the worst 10% of outcomes may be (the CVaR floor, in M€ of NPV). "
    "The optimiser then picks the PPA mix with the highest expected value that respects it."
)

rec = common.get_recommendation(zone)
note = common.floor_note(case, rec)
if note:
    st.info(note)
npv_offers, npv_merchant = common.get_npvs(zone)
alpha = case.market.cvar_alpha
names = [o.name for o in case.offers]
win_idx = names.index(rec.offer)
npv_win = npv_offers[:, [win_idx]]

lo = cvar(npv_merchant, alpha)
hi = max(max_cvar(npv_win, npv_merchant, alpha), lo, rec.cvar_floor)
lo = min(lo, rec.cvar_floor)
default = min(max(rec.cvar_floor, lo), hi)

if hi > lo:
    slider_m = st.slider(
        "CVaR floor (M€): worst-10% average NPV must stay above this",
        min_value=lo / MEUR, max_value=hi / MEUR, value=default / MEUR,
        step=(hi - lo) / MEUR / 100, key="cvar_floor",
    )
else:
    slider_m = lo / MEUR
    st.caption(f"CVaR floor fixed at {lo / MEUR:.2f} M€ (no offer improves on merchant risk).")
with st.expander("Advanced"):
    override_m = st.number_input(
        "CVaR floor override (M€, 0 = use the slider)", value=0.0, key="cvar_floor_override",
    )
floor = override_m * MEUR if override_m != 0 else min(slider_m * MEUR, hi)

single = optimise_allocation(npv_win, npv_merchant, floor, alpha)
multi = optimise_allocation(npv_offers, npv_merchant, floor, alpha)

if single.status == "infeasible" or multi.status == "infeasible":
    st.error(INFEASIBLE_MSG)
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Floor used", f"{floor / MEUR:.2f} M€")
    c2.metric("Expected NPV of the mix", f"{multi.expected / MEUR:.2f} M€")
    c3.metric("Worst-10% NPV of the mix", f"{multi.cvar / MEUR:.2f} M€")

    st.subheader("Recommended offer alone")
    st.markdown(f"Offer **{rec.offer}**: sign **{single.shares[0] * 100:.0f}%** of production, "
                f"the rest stays merchant ({(1 - single.shares[0]) * 100:.0f}%).")
    st.subheader("Best mix of all offers")
    shares = {n: float(s) for n, s in zip(names, multi.shares)}
    shares["Merchant (remainder)"] = max(0.0, 1.0 - sum(shares.values()))
    st.dataframe(
        pd.DataFrame({"share of production (%)": {k: round(v * 100, 1) for k, v in shares.items()}}),
        width="stretch",
    )

if rec.disagrees:
    st.info(
        "The score winner and the offer the optimiser prefers differ. The score also weighs "
        "non-financial criteria (counterparty rating, penalties, GoO, imbalance), while the "
        "optimiser looks at money and downside only."
    )

st.subheader("Expected value versus downside")
fr = common.get_frontier(zone)
fig = go.Figure(go.Scatter(x=fr["cvar"] / MEUR, y=fr["expected"] / MEUR, mode="lines+markers", name="Frontier"))
if multi.status == "optimal":
    fig.add_trace(go.Scatter(x=[multi.cvar / MEUR], y=[multi.expected / MEUR], mode="markers",
                             marker=dict(size=14, symbol="star"), name="Current floor"))
fig.update_layout(xaxis_title="Worst-10% average NPV (M€)", yaxis_title="Expected NPV (M€)")
st.plotly_chart(fig, width="stretch")

st.subheader("Break-even price per offer")
st.caption("Offer price at which the offer matches staying merchant on mean NPV.")
be = common.get_breakevens(zone)
st.dataframe(
    pd.DataFrame({
        "offer price (€/MWh)": {o.name: round(o.price, 1) for o in case.offers},
        "break-even (€/MWh)": {n: ("n/a" if v != v else round(v, 1)) for n, v in be.items()},
    }),
    width="stretch",
)
st.caption(common.SOURCES)
common.footer(case.is_synthetic)
