# Data sources

All sources are public. Check each source's terms before publishing data, and cite the source in every chart and deliverable.

| Data | Source | Access | Used by | Notes |
|---|---|---|---|---|
| Day-ahead prices by Italian bidding zone | ENTSO-E Transparency Platform, transparency.entsoe.eu | Free registration; REST API token requested by email to the ENTSO-E helpdesk | `scripts/build_data.py`, `src/ppa_italia/data/entsoe.py` | Python client `entsoe-py`. Zones NORD, CNOR, CSUD, SUD, CALA, SICI, SARD. Short gaps (up to 6 hours) are interpolated by the script; longer gaps stay missing. **Token not yet available: the app uses a labelled synthetic series** (`data/synthetic.py`) |
| Actual wind generation per zone | ENTSO-E Transparency Platform | Same token | (not built; out of scope) | The wind loader remains but the build pipeline no longer produces wind profiles |
| Solar production profile | PVGIS (EU Joint Research Centre), re.jrc.ec.europa.eu/pvg_tools | Free, no key | `scripts/build_puglia_profile.py`, `src/ppa_italia/data/pvgis.py` | Cite "PVGIS (c) European Union". The Puglia profile is precomputed in `data/precomputed/puglia_solar.parquet` |
| Imbalance prices | Terna, terna.it | Public downloads | `examples/puglia/assumptions.toml` | Placeholder (3.0 EUR/MWh) until sourced |
| Guarantees of origin | GSE; EEX auction results | Public | `examples/puglia/assumptions.toml` | Placeholder (1.0 EUR/MWh) until sourced |
| Italian market and regulation | GME, GSE, Terna, ARERA | Public | `docs/term-sheet-*.md` | Verify the current status of the PUN phase-out before relying on the change-in-law wording |
| Default probabilities | S&P Global Ratings annual default study (as cited in `credit.py`) | Public report | `src/ppa_italia/credit.py` | Edition and values to be verified |
| PPA price benchmarks | Press reports of LevelTen / Pexapark indices | Public articles | `docs/benchmarks.md` | One dated figure so far, with caveats |
| Italian zonal prices (cross-check only) | Energy-Charts (Fraunhofer ISE), api.energy-charts.info | No key | **Never used** | Licence for Italian zones: private and internal use only. No raw or derived data from it is stored or published |

## Open items

- **ENTSO-E licence decision (author, pending).** Read the ENTSO-E Transparency Platform terms of use and decide whether hourly prices may be redistributed in a public repository and app. If yes, ship the Parquet files. If not, apply the fallback in the design spec section 5.2: ship only zone-year aggregates and the Puglia results, plus a "paste your own token" input on the Asset page held in `st.session_state` only. Record the decision and the terms link here once made: decision: _pending_; link: _pending_.
- ENTSO-E API token not yet obtained; imbalance and GoO assumptions not yet sourced.

## Rules

- Raw downloads go in `data/raw/` and are not committed.
- Every assumption (imbalance cost, risk discount, GoO price) is written in `docs/methodology.md` and `examples/puglia/assumptions.toml` with its source, or marked as a placeholder.
- Numbers in deliverables are indicative and labelled as such.
