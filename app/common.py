"""Shared helpers for the Streamlit pages: cached example, header, offer editor parsing."""
from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from ppa_italia.credit import npv_net_of_credit
from ppa_italia.data import store
from ppa_italia.example import EXAMPLE_DIR, ExampleCase, load_example
from ppa_italia.hedge import frontier, merchant_breakeven_price
from ppa_italia.pricing import fair_floor_premium
from ppa_italia.recommend import Recommendation, recommend
from ppa_italia.scenarios import profile_on_years, to_8760
from ppa_italia.structures import Offer
from ppa_italia.zones import REGION_TO_ZONE, ZONE_SITE, zone_of
from ppa_italia.value import yearly_summary

DISCLAIMER = "Indicative, educational, built on public data. Not trading advice and not any company's pricing."
SYNTHETIC_LABEL = "SYNTHETIC — placeholder until ENTSO-E data"
TYPICAL_YEAR_NOTE = "Capture rates use a typical (median) weather year applied to every price year."
SOURCES = "Sources: PVGIS © European Union; ENTSO-E Transparency Platform."
DEFAULT_REGION = "Puglia"
IMBALANCE_NOTE = "Imbalance cost is a placeholder assumption: no imbalance prices are available for this zone."
EXAMPLE_OFFERS = EXAMPLE_DIR / "offers.csv"
DOCS = Path(__file__).resolve().parents[1] / "docs"
TERM_SHEETS = {"Term sheet — Puglia example (zone SUD), EN": DOCS / "term-sheet-en.md",
               "Term sheet — Puglia example (zone SUD), IT": DOCS / "term-sheet-it.md"}
STATIC_DOC_ZONE = "SUD"  # the term sheets and benchmarks were written for the Puglia (SUD) example
SOURCE_LABELS = {"file-library": "File Library", "api": "ENTSO-E API"}


# Caches live for the server process: restart the app after rebuilding the data.
@st.cache_resource
def get_example(zone: str) -> ExampleCase:
    """Load the example case for a zone once per server process."""
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
    """The zone's site solar profile (example capacity) stamped onto the zone's price years."""
    prices, _ = store.load_prices(zone)
    site = store.load_site_profile(zone) * get_example(zone).capacity_mw
    return align_to_prices(site, prices)


@st.cache_resource
def get_home_yearly(zone: str) -> pd.DataFrame:
    """Yearly capture summary of the example solar plant for a zone, on the aligned profile."""
    prices, _ = store.load_prices(zone)
    return yearly_summary(prices, get_aligned_solar(zone))


def region_selector() -> str:
    """Sidebar region selectbox (key "region", default Puglia); returns the region's bidding zone.

    Must be called first on every page. Streamlit drops a widget's keyed state when the
    page changes, so the value is re-assigned to itself every run to keep it across pages.
    """
    st.session_state.setdefault("region", DEFAULT_REGION)
    # Re-assigning keeps the value alive across pages (widget state is dropped on navigation).
    st.session_state["region"] = st.session_state["region"]
    region = st.sidebar.selectbox("Region of the asset", list(REGION_TO_ZONE), key="region")
    zone = zone_of(region)
    st.sidebar.caption(f"Bidding zone {zone}; solar site {ZONE_SITE[zone][0]}.")
    return zone


def status_notes(case: ExampleCase) -> list[str]:
    """Notes on which data components are real: zonal-solar fallback years and the imbalance placeholder.

    The synthetic-price banner is shown separately by `header`.
    """
    notes: list[str] = []
    if case.fallback_years:
        years = ", ".join(str(y) for y in case.fallback_years)
        notes.append(f"Zonal solar production is missing for {years}: those years use the PVGIS site profile "
                     f"({ZONE_SITE[case.zone][0]}) instead.")
    if case.imbalance_source != "computed":
        notes.append(IMBALANCE_NOTE)
    return notes


def load_case_or_stop(zone: str) -> ExampleCase:
    """The cached example for a zone; shows a visitor-friendly error and stops the page if its data is missing."""
    try:
        return get_example(zone)
    except FileNotFoundError:
        st.error("Data for this region is not available yet. Please choose another region. "
                 "(Maintainer: run scripts/build_data.py --sites.)")
        st.stop()


def footer_text(manifest: dict | None, zone: str, is_synthetic: bool = False) -> str:
    """Footer line: human source label, the zone's own price-file range and the build date."""
    suffix = " — prices for this region: synthetic placeholder" if is_synthetic else ""
    if not manifest:
        return "Data source: unknown (no manifest)" + suffix
    source = manifest.get("source", "?")
    label = SOURCE_LABELS.get(source, source)
    entry = manifest.get("files", {}).get(f"prices_{zone}.parquet")
    period = f"{entry['first'][:10]} → {entry['last'][:10]}" if entry else "no price file for this zone"
    built = str(manifest.get("built_utc", "?"))[:10]
    return f"Data: ENTSO-E Transparency Platform ({label}), {zone} prices {period}, built {built}{suffix}"


def footer(zone: str, is_synthetic: bool = False) -> None:
    """Caption naming the data source, the zone's price period and the build date from the manifest."""
    st.caption(footer_text(store.load_manifest(), zone, is_synthetic))


def floor_note(case: ExampleCase, rec: Recommendation) -> str | None:
    """Explanation shown when the default CVaR floor target is not reachable with these offers."""
    if not rec.floor_capped:
        return None
    gamma = case.market.cvar_floor_share_of_mean
    merchant_mean = float(get_npvs(case.zone)[1].mean())
    reached = rec.cvar_floor / merchant_mean * 100 if merchant_mean > 0 else float("nan")
    return (f"The bank-style target (worst-10% NPV at least {gamma * 100:.0f}% of the mean merchant NPV) is not "
            f"reachable with these offers. The recommendation hedges as much as possible, reaching "
            f"{reached:.0f}% (best achievable worst-10% NPV over mean merchant NPV).")


@st.cache_resource
def get_npvs(zone: str) -> tuple[np.ndarray, np.ndarray]:
    """NPV net of credit loss per scenario: (n, k) for the example offers, (n,) all-merchant.

    Same objective as recommend(), so Home, Hedge and Report agree.
    """
    case = get_example(zone)
    sc, m, h = case.scenarios, case.market, case.horizon
    offers = np.column_stack([npv_net_of_credit(o, sc, m, h) for o in case.offers])
    return offers, npv_net_of_credit(None, sc, m, h)


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


def header(title: str, case: ExampleCase) -> None:
    """Page title, disclaimer, the synthetic-price banner and the per-component data notes (all st.info)."""
    st.title(title)
    st.caption(DISCLAIMER)
    if case.is_synthetic:
        st.info(SYNTHETIC_LABEL)
    for note in status_notes(case):
        st.info(note)


def headline(rec: Recommendation, offer: Offer | None = None, avg_mw: float | None = None) -> str:
    """The one-sentence recommendation shown on Home.

    A baseload offer is a fixed block, so "100%" would be misleading: the text names the block
    (MW and share of average output) and says the full contracted volume (or its share) is used.
    """
    fair = f"Fair pay-as-produced price range {rec.fair_low:.1f}–{rec.fair_mid:.1f} €/MWh."
    robust = f"Recommendation robust in {rec.win_share * 100:.0f}% of weightings."
    if rec.share < 0.01:
        return f"Stay merchant for now; best offer if hedging: {rec.offer}. {fair} {robust}"
    if offer is not None and offer.structure == "baseload" and offer.baseload_mw > 0 and avg_mw:
        block = f"a {offer.baseload_mw:.1f} MW baseload block (about {offer.baseload_mw / avg_mw * 100:.0f}% of average output)"
        volume = ("for the full contracted volume" if rec.share >= 0.995
                  else f"for {rec.share * 100:.0f}% of the contracted volume")
        return f"Sign offer {rec.offer} — {block} — {volume}. {fair} {robust}"
    return f"Sign offer {rec.offer} for {rec.share * 100:.0f}% of production. {fair} {robust}"


def breakeven_line(rec: Recommendation, structure: str) -> str:
    """Merchant break-even sentence; for a floor offer the break-even is a floor level."""
    be = "n/a" if rec.breakeven != rec.breakeven else f"{rec.breakeven:.1f} €/MWh"
    label = " (floor level)" if structure == "floor" else ""
    return f"Merchant break-even price{label} of offer {rec.offer}: {be}"


def offer_by_name(offers: list[Offer], name: str) -> Offer:
    """The offer called `name` (the recommendation stores only the name)."""
    return next(o for o in offers if o.name == name)


def static_doc_caption(zone: str, what: str) -> str | None:
    """Caption warning that a static document is the Puglia (SUD) example, or None when the zone is SUD."""
    if zone == STATIC_DOC_ZONE:
        return None
    return (f"The {what} is the Puglia worked example (zone SUD), not this region. "
            f"This region's numbers (zone {zone}) are in the headline and the PDF report.")


def term_sheet_expanders(zone: str = STATIC_DOC_ZONE) -> None:
    """Render the EN and IT one-page term sheets from docs/ in two expanders (Puglia example, flagged for other zones)."""
    note = static_doc_caption(zone, "term sheet")
    if note:
        st.caption(note)
    for label, path in TERM_SHEETS.items():
        with st.expander(label):
            st.markdown(path.read_text(encoding="utf-8"))


def assumption_lines(case: ExampleCase, rec: Recommendation) -> list[str]:
    """The zone's data-derived assumptions as readable lines (imbalance, band, fee, floor premium, CVaR target, gaps)."""
    m, sc = case.market, case.scenarios
    src = ("computed from ENTSO-E imbalance prices" if case.imbalance_source == "computed"
           else "placeholder, no imbalance prices for this zone")
    lines = [f"Imbalance cost: {m.imbalance_cost:.2f} €/MWh ({src}); forecast error ε = {m.imbalance_error_share * 100:.0f}% of output."]
    factors = sc.level_factors or (1.0,)
    band = (max(factors) - min(factors)) / 2 * 100
    lines.append(f"Price-level band: ±{band:.0f}% around the trailing 12-month baseload of {sc.reference_level:.1f} €/MWh; "
                 f"{len(sc.prices)} scenarios ({len(factors)} price levels).")
    with open(EXAMPLE_OFFERS, newline="", encoding="utf-8") as f:
        rows = {r["name"]: r for r in csv.DictReader(f)}
    for o in case.offers:
        fee_pct = float(rows[o.name]["balancing_fee_pct_of_cost"])
        if fee_pct > 0 and o.imbalance_on_buyer:
            lines.append(f"Balancing fee, offer {o.name}: {fee_pct:.0f}% of the imbalance cost = "
                         f"{fee_pct / 100 * m.imbalance_cost:.2f} €/MWh.")
        if o.structure == "floor":
            fair = fair_floor_premium(o, sc)
            lines.append(f"Floor premium, offer {o.name}: fair {fair:.2f} €/MWh; applied {o.floor_premium:.2f} €/MWh "
                         f"({rows[o.name]['floor_premium_pct_of_fair']}% of fair plus the balancing fee).")
    capped = "reached only partly: the target was capped" if rec.floor_capped else "reachable, not capped"
    lines.append(f"Bank-style CVaR target γ = {m.cvar_floor_share_of_mean * 100:.0f}% of the mean merchant NPV "
                 f"(worst {m.cvar_alpha * 100:.0f}% of scenarios): {capped}.")
    years = ", ".join(str(y) for y in case.fallback_years) or "none"
    lines.append(f"Years on the PVGIS site profile instead of zonal solar (fallback): {years}.")
    return lines


CRITERIA_LABELS = {
    "npv_mean": "Mean NPV (M€)",
    "npv_p10": "P10 NPV (M€)",
    "credit_el": "Expected credit loss (M€)",
    "tenor_years": "Tenor (years)",
    "indexation_pct": "Indexation (%/yr)",
    "imbalance_on_buyer": "Imbalance on buyer",
    "penalty_severity": "Penalty severity (1-5)",
}
MEUR_COLUMNS = ("npv_mean", "npv_p10", "credit_el")


def criteria_for_display(table: pd.DataFrame) -> pd.DataFrame:
    """Criteria table with money in M€, indexation in %, yes/no flags and readable column names."""
    out = table.copy()
    for col in MEUR_COLUMNS:
        out[col] = (out[col] / 1e6).round(3)
    out["indexation_pct"] = (out["indexation_pct"] * 100).round(1)
    out["imbalance_on_buyer"] = out["imbalance_on_buyer"].map({1: "yes", 0: "no"})
    return out.rename(columns=CRITERIA_LABELS)


def win_share_bar_text(wins: pd.Series, threshold: float) -> list[str]:
    """Bar labels for the win-share chart: 'fragile' on the winner's bar when it is below threshold."""
    return ["fragile" if i == 0 and v < threshold else "" for i, v in enumerate(wins.values)]


def offers_to_frame(offers: list[Offer]) -> pd.DataFrame:
    """Offers as a DataFrame whose columns are exactly the Offer field names."""
    return pd.DataFrame([dataclasses.asdict(o) for o in offers])


def offers_from_editor(df: pd.DataFrame) -> tuple[list[Offer], list[str]]:
    """Turn editor rows into Offers; bad rows become 'Row i (name): error' strings.

    A name already used by an earlier valid row is rejected as a duplicate.
    """
    offers: list[Offer] = []
    errors: list[str] = []
    for i, row in enumerate(df.to_dict("records"), start=1):
        empty = [k for k, v in row.items() if v is None or pd.isna(v)]
        if empty:
            errors.append(f"Row {i} ({row.get('name')}): {empty[0]} is empty")
            continue
        if any(o.name == row["name"] for o in offers):
            errors.append(f"Row {i} ({row['name']}): duplicate name")
            continue
        try:
            offers.append(Offer(**row))
        except (ValueError, TypeError) as err:
            errors.append(f"Row {i} ({row.get('name')}): {err}")
    return offers, errors
