"""Shared helpers for the Streamlit pages: cached example, header, offer editor parsing."""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import streamlit as st

from ppa_italia.data import store
from ppa_italia.example import ExampleCase, load_example
from ppa_italia.hedge import frontier, merchant_breakeven_price
from ppa_italia.recommend import Recommendation, recommend
from ppa_italia.scenarios import profile_on_years, to_8760
from ppa_italia.structures import Offer, npv
from ppa_italia.value import yearly_summary

DISCLAIMER = "Indicative, educational, built on public data. Not trading advice and not any company's pricing."
SYNTHETIC_LABEL = "SYNTHETIC — placeholder until ENTSO-E data"
TYPICAL_YEAR_NOTE = "Capture rates use a typical (median) weather year applied to every price year."
SOURCES = "Sources: PVGIS © European Union; ENTSO-E Transparency Platform."
DEFAULT_ZONE = "SUD"


@st.cache_resource
def get_example(zone: str) -> ExampleCase:
    """Load the Puglia example for a zone once per server process."""
    return load_example(zone)


@st.cache_resource
def get_recommendation(zone: str) -> Recommendation:
    """Run the (expensive) recommendation chain once per zone with the default weights."""
    case = get_example(zone)
    return recommend(case.offers, case.scenarios, case.market, case.horizon)


def align_to_prices(gen: pd.Series, prices: pd.Series) -> pd.Series:
    """Re-stamp a typical (median) weather year onto every calendar year present in the prices."""
    return profile_on_years(gen, sorted(set(prices.index.year)))


def weather_year_energy(gen: pd.Series) -> pd.Series:
    """Annual energy (MWh) of each complete weather year; the basis for P50/P90."""
    return pd.Series({y: float(v.sum()) for y, v in to_8760(gen).items()})


@st.cache_resource
def get_aligned_solar(zone: str) -> pd.Series:
    """The Puglia solar profile stamped onto the zone's price years."""
    prices, _ = store.load_prices(zone)
    return align_to_prices(store.load_solar_puglia(), prices)


@st.cache_resource
def get_home_yearly(zone: str) -> pd.DataFrame:
    """Yearly capture summary of the example solar plant for a zone, on the aligned profile."""
    prices, _ = store.load_prices(zone)
    return yearly_summary(prices, get_aligned_solar(zone))


@st.cache_resource
def get_npvs(zone: str) -> tuple[np.ndarray, np.ndarray]:
    """NPV per scenario: (n, k) matrix for the example offers and the (n,) all-merchant vector."""
    case = get_example(zone)
    sc, m, h = case.scenarios, case.market, case.horizon
    offers = np.column_stack([npv(o, sc, m, h) for o in case.offers])
    return offers, npv(None, sc, m, h)


@st.cache_resource
def get_frontier(zone: str) -> pd.DataFrame:
    """Expected-vs-CVaR frontier of all example offers."""
    offers, merchant = get_npvs(zone)
    return frontier(offers, merchant, alpha=get_example(zone).market.cvar_alpha)


@st.cache_resource
def get_breakevens(zone: str) -> dict[str, float]:
    """Merchant break-even price per example offer; NaN where none exists."""
    case = get_example(zone)
    out: dict[str, float] = {}
    for o in case.offers:
        try:
            out[o.name] = merchant_breakeven_price(o, case.scenarios, case.market, case.horizon)
        except ValueError:
            out[o.name] = float("nan")
    return out


def header(title: str, is_synthetic: bool) -> None:
    """Page title, disclaimer, and the synthetic-data banner when prices are placeholders."""
    st.title(title)
    st.caption(DISCLAIMER)
    if is_synthetic:
        st.info(SYNTHETIC_LABEL)


def headline(rec: Recommendation) -> str:
    """The one-sentence recommendation shown on Home."""
    fair = f"Fair price range {rec.fair_low:.1f}–{rec.fair_mid:.1f} €/MWh."
    robust = f"Recommendation robust in {rec.win_share * 100:.0f}% of weightings."
    if rec.share < 0.01:
        return f"Stay merchant for now; best offer if hedging: {rec.offer}. {fair} {robust}"
    return f"Sign offer {rec.offer} for {rec.share * 100:.0f}% of production. {fair} {robust}"


def win_share_bar_text(wins: pd.Series, threshold: float) -> list[str]:
    """Bar labels for the win-share chart: 'fragile' on the winner's bar when it is below threshold."""
    return ["fragile" if i == 0 and v < threshold else "" for i, v in enumerate(wins.values)]


def offers_to_frame(offers: list[Offer]) -> pd.DataFrame:
    """Offers as a DataFrame whose columns are exactly the Offer field names."""
    return pd.DataFrame([dataclasses.asdict(o) for o in offers])


def offers_from_editor(df: pd.DataFrame) -> tuple[list[Offer], list[str]]:
    """Turn editor rows into Offers; bad rows become 'Row i (name): error' strings."""
    offers: list[Offer] = []
    errors: list[str] = []
    for i, row in enumerate(df.to_dict("records"), start=1):
        empty = [k for k, v in row.items() if v is None or pd.isna(v)]
        if empty:
            errors.append(f"Row {i} ({row.get('name')}): {empty[0]} is empty")
            continue
        try:
            offers.append(Offer(**row))
        except (ValueError, TypeError) as err:
            errors.append(f"Row {i} ({row.get('name')}): {err}")
    return offers, errors
