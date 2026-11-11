"""Report: download the customer PDF in Italian or English."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make app/common.py importable

import streamlit as st  # noqa: E402

import common  # noqa: E402
from ppa_italia.report import build_report  # noqa: E402

st.set_page_config(page_title="Report", layout="wide")

zone = common.DEFAULT_ZONE
case = common.get_example(zone)
common.header("Report", case.is_synthetic)
st.caption(common.TYPICAL_YEAR_NOTE)

choice = st.radio("Language", ["Italiano", "English"], horizontal=True, key="report_lang")
lang = "it" if choice == "Italiano" else "en"

rec = common.get_recommendation(zone)
summary = common.get_home_yearly(zone)
pdf = build_report(rec, summary, zone, lang, case.is_synthetic)
st.download_button(
    "Download PDF", data=pdf, file_name=f"ppa-italia-report-{lang}.pdf", mime="application/pdf",
)
st.caption(common.SOURCES)
