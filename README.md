# Sundial

[![CI](https://github.com/vincenzotestini02-spec/Sundial/actions/workflows/ci.yml/badge.svg)](https://github.com/vincenzotestini02-spec/Sundial/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*Route-to-market and PPA valuation for Italian renewables. Like a sundial, it reads the sun to tell you what your power is worth.*

A Python package and Streamlit app that values Italian renewable power purchase agreements (PPAs) and turns a set of offers into one recommendation.

> Indicative, educational, built on public data. Not trading advice and not any company's pricing.

## The 30-second view

**The customer's question:** a 20 MW solar park in Puglia (zone SUD) has received three PPA offers. Which one should it sign, for how much of its production, and what is a fair price? The sidebar region selector re-runs the whole analysis for any of the 20 Italian regions (7 bidding zones), each with its own prices, solar shape, imbalance cost and representative site.

**Headline on real ENTSO-E data (zone SUD, Foggia site):**
Sign offer B for 100% of production. Fair pay-as-produced price range 81.7 to 120.9 EUR/MWh. Recommendation robust in 87% of weightings. Merchant break-even of offer B: 142.1 EUR/MWh, just above its 140.7 EUR/MWh price, so B gives up about 0.4% of expected value (28.96 vs 29.08 M EUR NPV) to lift the average of the worst 10% of scenarios from 18.7 to 22.1 M EUR.

Offer B is a 7-year baseload block (1.67 MW, half of average output) at 95% of the trailing 12-month baseload price, indexed at 2% a year, A-rated buyer, GoOs included, imbalance stays with the seller. The bank-style hedge target (worst-10% NPV at least 85% of the expected merchant NPV) is not reachable with these offers in any zone, so the recommendation hedges as much as the offers allow (76% in SUD). See the one-page term sheet: [English](docs/term-sheet-en.md), [Italiano](docs/term-sheet-it.md).

> **Status:** real ENTSO-E day-ahead prices, zonal solar generation and imbalance prices for all seven zones (2021 to November 2026). Zonal solar is incomplete for Sardinia, which falls back to the PVGIS shape for 2022-2025 (see Limitations). The offers, buyers and the price-level band are assumptions, not market data.

| App | _link to be added after deployment_ (Streamlit Community Cloud apps sleep when idle; wake-up takes up to about a minute) |
| Screenshot 1: Home | _to be added_ |
| Screenshot 2: Compare offers and robustness | _to be added_ |
| Screenshot 3 / GIF: Hedge frontier and report | _to be added_ |

## How it works

The chain runs in one direction so that Home, the report and the term sheet agree:

1. **Structures and credit** give each offer an expected revenue, a P10 (downside) revenue and an expected credit loss.
2. **Tender scoring** ranks the offers on those and on contract terms; its winner is the recommended offer. A Dirichlet weight-perturbation test reports how often it still wins.
3. **Hedge LP** sizes how much production goes under the winner, subject to a CVaR floor on the worst 10% of scenarios. Scenario NPVs are net of each offer's expected credit loss.
4. **Fair pay-as-produced price** is the capture price net of imbalance and margin, plus GoO value, with a low end from the scenario spread. The merchant breakeven is shown as a check.

Package `src/ppa_italia/`:

| Module | Role |
|---|---|
| `data/` | ENTSO-E (File Library and API) loaders and build, PVGIS loader, data store, synthetic fallback |
| `zones.py` | region to bidding-zone mapping and one representative solar site per zone |
| `imbalance.py` | imbalance cost per zone from real imbalance prices |
| `value.py` | capture price and rate, zero/negative-price exposure |
| `scenarios.py` | "historical shape, current level" price scenarios: same-year zonal solar shape, PVGIS weather-year energy, three price levels |
| `structures.py` | revenue and NPV for pay-as-produced, baseload and floor PPAs |
| `credit.py` | expected credit loss by rating |
| `tender.py` | multi-criteria scoring and weight robustness |
| `hedge.py` | CVaR-constrained allocation LP, frontier, breakeven |
| `pricing.py` | fair price range, fair floor premium, trailing-capture backtest |
| `recommend.py` | the single recommendation |
| `report.py`, `report_text.py` | two-page customer PDF in Italian and English |

Streamlit app (`app/`): Home, Asset value, Compare offers, Hedge, Backtest and checks, Report. The Puglia example (zone SUD) is pre-loaded on every page, so the app works with no input; the footer shows the data source and period from `manifest.json`. Models and their limits: [docs/methodology.md](docs/methodology.md).

**CBS Energy Economics minor: where it shows**

| Course | Where in the app |
|---|---|
| Energy Economics, Markets, and Policy | Merit order and solar cannibalisation: capture rate and zero/negative-price hours (Asset value) |
| Energy System Economics and Modelling | The optimisation model: LP allocation across offers and merchant with a CVaR floor (Hedge) |
| The Energy Industry in Transition | Why an owner must choose a route to market, and how the answer is framed for a customer (Home, Report, term sheet) |

## Data and licences

- **ENTSO-E Transparency Platform**: day-ahead prices, actual solar generation and imbalance prices for the seven Italian zones. Built from the ENTSO-E File Library (no token) or from the API (free token); both give identical files. Publication of the derived Parquet files in this repository is allowed per the author's reading of the ENTSO-E terms of use.
- **PVGIS**, (c) European Union: solar production profile of one representative site per zone (weather years 2005-2023). Free, keyless.
- **Energy-Charts** is never used: its licence for Italian zones is private and internal use only.
- **Synthetic fallback:** a zone without real price files gets a labelled synthetic series (`data/synthetic.py`) and every page says so. The shipped data cover all seven zones.

All sources, folder names and build commands: [docs/data-sources.md](docs/data-sources.md). Price benchmarks: [docs/benchmarks.md](docs/benchmarks.md).

## Checks

All results below are on real ENTSO-E data, zone SUD unless stated.

| What | Judge | Result |
|---|---|---|
| All models | Unit tests with hand-computed answers, run in CI | 168 tests pass |
| Zonal prices | Yearly means vs GME PUN annual means 2021-2025 (125.46, 303.95, 127.24, 108.52, 115.94 EUR/MWh), tolerance +-5% | All 7 zones within +-5% except SARD 2022 (287.0, -5.6%), reported as is |
| Solar profile | Specific yield vs plausible Puglia fixed-tilt range of 1,400-1,600 kWh/kWp | 1,467 kWh/kWp (Foggia, PVGIS 2005-2023), pass |
| Imbalance cost | Computed from real imbalance prices: 10% forecast miss x solar-weighted mean abs(imbalance - day-ahead), last 24 complete months | 6.35 EUR/MWh in SUD (5.11 NORD to 6.61 SARD), replaces the 3.0 placeholder |
| Fair floor premium | Expected value of the put the floor grants, over all 285 scenarios | 7.76 EUR/MWh in SUD; offer C is priced at 120% of it plus the balancing fee |
| Pricing anchor | Backtest of "last year's capture price" | Mean absolute error 79.8 EUR/MWh over 2022-2026, driven by the 2022 crisis (+180 and -180 EUR/MWh around it); -14.6, +2.2 and +21.1 EUR/MWh for 2024-2026 (2026 to 12 Nov). A naive anchor fails when the price level moves, which is why scenarios use a stated level band |
| Fair PPA range | LevelTen Q4 2025 Italy solar PPA index, 60.67 EUR/MWh (via pv magazine) | The app's 81.7-120.9 EUR/MWh is above it. Not like for like: the index percentile, contract length and structure are not defined in the source, and the period differs (Q4 2025 vs a trailing 12-month baseload of 148.1 EUR/MWh to November 2026). An order-of-magnitude check only, see [docs/benchmarks.md](docs/benchmarks.md) |
| Recommendation | Weight robustness, at least 70% win share or labelled fragile | 87% in SUD, 86-89% in all zones, pass |
| Hedge target | Worst-10% NPV at least 85% of expected merchant NPV (bank-style, stated assumption) | Not reachable in any zone: best achievable is 74-76% of the mean (SUD 75.9%). Reported as a miss; the recommendation hedges as much as possible |
| Hedge LP | Sanity cases in tests (floor at 0 gives all merchant if merchant mean is higher; floor at max gives full hedge) | Tests pass |

A missed target reported with real numbers counts as a pass for honesty. Nothing is reported as passed that was not run.

## Quick start

```bash
pip install -e ".[dev]"
python -m pytest
streamlit run app/Home.py
```

The repository ships the built data for all seven zones in `data/precomputed/`. To rebuild, run one command from either source (both write identical files; `manifest.json` records which was used):

```bash
# ENTSO-E File Library zips (no token)
python scripts/build_data.py --source file-library --prices-zips data/raw/energyprices.zip \
    --solar-zips data/raw/gen.zip --imbalance-zips data/raw/ImbalacePrices2.zip --sites
# ENTSO-E API (free token in ENTSOE_TOKEN)
python scripts/build_data.py --source api --start 2021-01 --sites
```

`--sites` adds the PVGIS solar profile of each zone (no key). `SUNDIAL_DATA_DIR` points the app at another data folder; `SUNDIAL_FORCE_SYNTHETIC=1` forces the labelled synthetic prices.

## AI-assisted parts

The code and the first drafts of the documentation were generated with AI assistance (Claude), under a reviewed, test-first process: tests written first, then code, then review. The author must still verify:

- the Italian copy (`report_text.py`, `docs/term-sheet-it.md`);
- every sourced assumption (GoO value, default probabilities, margin, the +-30% price-level band, the 110% balancing fee) and replace the placeholders;
- the clause list against the current EFET Corporate PPA template (its current version could not be opened during drafting).

## Limitations

- Price scenarios take history for the shape and the trailing 12-month baseload (148.1 EUR/MWh in SUD) for the level, then repeat every scenario at -30%, 0% and +30%. The band is a stated assumption, not a forecast or a forward curve; the hedge result depends on it.
- The default hedge target (85% of expected merchant NPV for the worst 10%) is a bank-style assumption. It is unreachable on real data, so the share is set by the best achievable tail, not by the target.
- The zonal solar shape (fleet average) is applied to a single representative site per zone; PVGIS gives the energy of 19 weather years. Local curtailment and site-specific shape are not modelled.
- Sardinia (SARD) lacks complete zonal solar for 2022-2025; those years use the PVGIS shape instead.
- The imbalance cost is a proxy (10% forecast miss at the Italian single imbalance price), and the 110% balancing fee for offers that move imbalance to the buyer is an example assumption.
- The scenario set is 285 equally weighted scenarios from 5 price years, so CVaR is still noisy and the price years are not independent draws.
- Credit uses a rating-based default table with one LGD; no collateral or rating migration.
- The offers and the buyer are fictional.

Details: [docs/methodology.md](docs/methodology.md).

---

Indicative, educational, built on public data. Not trading advice and not any company's pricing.

## Licence

Code: [MIT](LICENSE). Data keep their own terms (see *Data and licences*); bundled DejaVu fonts: see `assets/fonts/LICENSE-DejaVu.txt`.
