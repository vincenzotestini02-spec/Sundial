"""Compare offers: editable offer table, criteria, weights, scores and robustness."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.structures import RATINGS  # noqa: E402
from ppa_italia.tender import (  # noqa: E402
    DEFAULT_WEIGHTS,
    FRAGILE_THRESHOLD,
    HIGHER_IS_BETTER,
    criteria_table,
    rank_stability,
    score,
)

st.set_page_config(page_title="Compare offers", layout="wide")

zone = common.DEFAULT_ZONE
case = common.get_example(zone)
common.header("Compare offers", case.is_synthetic)
st.write("Edit the offers below (price in €/MWh), then adjust the weights. Needs at least 2 valid offers.")

edited = st.data_editor(
    common.offers_to_frame(case.offers),
    num_rows="dynamic",
    width="stretch",
    column_config={
        "structure": st.column_config.SelectboxColumn("structure", options=["pap", "baseload", "floor"]),
        "rating": st.column_config.SelectboxColumn("rating", options=list(RATINGS)),
    },
)
offers, errors = common.offers_from_editor(edited)
for e in errors:
    st.error(e)
if len(offers) < 2:
    st.info("At least 2 valid offers are needed to compare.")
    st.stop()

st.subheader("Weights")
cols = st.columns(len(DEFAULT_WEIGHTS))
weights = {
    name: col.slider(name, 0.0, 1.0, float(default), 0.05, key=f"w_{name}")
    for (name, default), col in zip(DEFAULT_WEIGHTS.items(), cols)
}
if sum(weights.values()) <= 0:
    st.info("Set at least one weight above zero.")
    st.stop()

try:
    table = criteria_table(offers, case.scenarios, case.market, case.horizon)
    scores = score(table, weights, HIGHER_IS_BETTER)
    wins = rank_stability(table, weights, HIGHER_IS_BETTER)
except ValueError as err:  # e.g. duplicate offer names
    st.error(f"Could not compare these offers: {err}")
    st.stop()

st.subheader("Criteria")
st.dataframe(table.round(2), width="stretch")

left, right = st.columns(2)
fig = go.Figure(go.Bar(x=scores.index, y=scores.values))
fig.update_layout(title="Weighted score (0 to 1, higher is better)", yaxis_title="score")
left.plotly_chart(fig, width="stretch")

fig = go.Figure(go.Bar(x=wins.index, y=wins.values, text=common.win_share_bar_text(wins, FRAGILE_THRESHOLD),
                       textposition="outside"))
fig.add_hline(y=FRAGILE_THRESHOLD, line_dash="dash", annotation_text="0.70 — below = fragile")
fig.update_layout(title="Win share across 5,000 perturbed weightings", yaxis_title="share of draws won",
                  yaxis_range=[0, 1])
right.plotly_chart(fig, width="stretch")

winner = wins.index[0]
if wins.iloc[0] < FRAGILE_THRESHOLD:
    st.markdown(f"Winner {winner} is **fragile**: it wins in only {wins.iloc[0] * 100:.0f}% of weightings.")
else:
    st.markdown(f"Winner {winner} is robust: it wins in {wins.iloc[0] * 100:.0f}% of weightings.")
st.caption(common.SOURCES)
